"""Dashboard page callbacks for KPI and chart updates based on filters"""

import re as _re
import pandas as pd
from pandas.api.types import is_string_dtype, is_numeric_dtype
from concurrent.futures import ThreadPoolExecutor, as_completed
from dash import Input, Output, State, ALL, callback, dcc, html
import dash
import dash_bootstrap_components as dbc
import plotly.express as px

from core.config import TEXT, TEXT_LIGHT, PRIMARY, BORDER, NAVY, GOLD, CHARCOAL, SUCCESS, WARNING, DANGER
from core.formatters import Formatter


def _fmt(val) -> str:
    """Format a number with K/M abbreviation."""
    try:
        v = float(val)
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if abs(v) >= 1_000:
            return f"{v/1_000:.1f}K"
        return f"{v:,.1f}"
    except Exception:
        return str(val)


def _safe_nums(raw) -> list:
    """Safely convert any Plotly data field (list, numpy array, None) to Python floats.

    Replaces the `(trace.get('y') or [])` pattern which raises
    'truth value of array is ambiguous' when raw is a numpy array.
    """
    if raw is None:
        return []
    # numpy array → Python list first
    if hasattr(raw, 'tolist'):
        raw = raw.tolist()
    result = []
    for v in raw:
        try:
            fv = float(v)
            if fv == fv:   # exclude NaN (NaN != NaN)
                result.append(fv)
        except (TypeError, ValueError):
            pass
    return result


def _safe_list(raw) -> list:
    """Convert any Plotly field (list, numpy array, None) to a plain Python list."""
    if raw is None:
        return []
    if hasattr(raw, 'tolist'):
        return raw.tolist()
    return list(raw)


def _pareto_cutoff(sorted_vals, threshold=0.8):
    """Return how many top items cover `threshold` of total."""
    total = sum(sorted_vals)
    if not total:
        return 0
    running = 0
    for i, v in enumerate(sorted_vals, 1):
        running += v
        if running / total >= threshold:
            return i
    return len(sorted_vals)


def _describe_figure(fig: dict, df=None) -> str:
    """
    Produce consulting-grade analytical insight from a Plotly figure dict.
    Uses actual plotted data arrays — no LLM required, instant, always accurate.
    """
    if not fig or 'data' not in fig:
        return ""
    traces = fig.get('data', [])
    if not traces:
        return ""

    trace = traces[0]
    chart_type = trace.get('type', 'bar')
    layout = fig.get('layout', {})
    title_raw = layout.get('title', {})
    title_text = (title_raw.get('text', '') if isinstance(title_raw, dict) else str(title_raw or ''))

    try:
        # ── BAR CHART ────────────────────────────────────────────────
        if chart_type == 'bar':
            x_vals = _safe_list(trace.get('x'))
            y_vals = _safe_nums(trace.get('y'))
            if not x_vals or not y_vals:
                return ""

            # Temporal bar charts (months, quarters, fiscal periods) — trend analysis
            if _is_temporal_x(x_vals) and len(y_vals) >= 3:
                n = len(y_vals)
                total = sum(y_vals)
                first_v, last_v = y_vals[0], y_vals[-1]
                pct_change = round((last_v - first_v) / first_v * 100, 1) if first_v else 0
                direction = "upward" if pct_change > 5 else "downward" if pct_change < -5 else "relatively flat"
                peak_v = max(y_vals)
                peak_idx = y_vals.index(peak_v)
                peak_label = x_vals[peak_idx] if peak_idx < len(x_vals) else f"period {peak_idx + 1}"
                avg_v = total / n
                # Coefficient of variation — stability measure
                try:
                    import statistics as _st
                    stdev_v = _st.stdev(y_vals)
                    cv = stdev_v / avg_v * 100 if avg_v else 0
                except Exception:
                    cv = 0
                stability = ("stable" if cv < 20 else "moderately volatile" if cv < 50 else "highly volatile")

                trend_desc = (f"{'gained' if pct_change > 0 else 'declined'} {abs(pct_change)}%"
                              if abs(pct_change) > 1 else "held steady")
                parts = [
                    f"Trend is {direction} — values {trend_desc} from {_fmt(first_v)} to {_fmt(last_v)} "
                    f"across {n} periods (avg {_fmt(avg_v)}).",
                    f"Peak of {_fmt(peak_v)} recorded at '{peak_label}'.",
                    f"Growth is {stability} (CV={cv:.0f}%).",
                ]
                return " ".join(parts)

            # Categorical bar — Pareto / concentration analysis
            pairs = sorted(zip(x_vals, y_vals), key=lambda p: p[1], reverse=True)
            labels, values = zip(*pairs)
            total = sum(values)
            top_pct = round(values[0] / total * 100, 1) if total else 0
            n80 = _pareto_cutoff(values)
            tail_count = len(values) - n80
            tail_pct = round((total - sum(values[:n80])) / total * 100, 1) if total else 0

            if top_pct >= 70:
                concentration = (f"highly concentrated — '{labels[0]}' alone commands {top_pct}% of total, "
                                 f"signalling a dominant player or primary workflow")
            elif top_pct >= 40:
                concentration = (f"moderately concentrated — '{labels[0]}' leads at {top_pct}%, with "
                                 f"top {min(n80, len(labels))} categories covering ~80% of activity")
            else:
                concentration = (f"broadly distributed across {len(labels)} categories — "
                                 f"no single entity dominates; '{labels[0]}' at {top_pct}%")

            parts = [f"Distribution is {concentration} ({_fmt(total)} total)."]
            if len(values) >= 2:
                ratio = round(values[0] / values[1], 1) if values[1] else 0
                parts.append(
                    f"'{labels[0]}' ({_fmt(values[0])}) outpaces runner-up "
                    f"'{labels[1]}' ({_fmt(values[1])}) by {ratio}×."
                )
            if tail_count > 0:
                qualifier = "just " if tail_pct < 5 else ""
                parts.append(
                    f"Remaining {tail_count} categor{'y' if tail_count == 1 else 'ies'} "
                    f"contribute {qualifier}{tail_pct}%."
                )
            return " ".join(parts)

        # ── HISTOGRAM ────────────────────────────────────────────────
        elif chart_type == 'histogram':
            x_vals = _safe_nums(trace.get('x'))
            if not x_vals:
                return ""
            import statistics
            mean_v = statistics.mean(x_vals)
            median_v = statistics.median(x_vals)
            try:
                stdev_v = statistics.stdev(x_vals)
            except Exception:
                stdev_v = 0
            skew_dir = "right-skewed (high-value outliers pulling the mean up)" if mean_v > median_v * 1.1 \
                       else "left-skewed (low-value outliers pulling the mean down)" if mean_v < median_v * 0.9 \
                       else "approximately symmetric"
            cv = stdev_v / mean_v * 100 if mean_v else 0
            variability = "low variability (consistent values)" if cv < 30 \
                          else "moderate variability" if cv < 80 \
                          else "high variability (wide spread of values)"
            return (
                f"Distribution of {_fmt(len(x_vals))} values — mean {_fmt(mean_v)}, median {_fmt(median_v)}. "
                f"The data is {skew_dir}, indicating {variability} (CV={cv:.0f}%). "
                f"Range spans {_fmt(min(x_vals))} to {_fmt(max(x_vals))}."
            )

        # ── PIE / DONUT ───────────────────────────────────────────────
        elif chart_type == 'pie':
            labels = _safe_list(trace.get('labels'))
            values = _safe_nums(trace.get('values'))
            if not labels or not values:
                return ""
            pairs = sorted(zip(labels, values), key=lambda p: p[1], reverse=True)
            lbls, vals = zip(*pairs)
            total = sum(vals)
            top_pct = round(vals[0] / total * 100, 1)
            top2_pct = round(sum(vals[:2]) / total * 100, 1) if len(vals) >= 2 else top_pct

            if top_pct >= 50:
                dominance = f"'{lbls[0]}' is the dominant segment, holding {top_pct}% share"
            else:
                dominance = f"'{lbls[0]}' leads with {top_pct}% — no single segment holds majority"

            hhi = sum((v / total * 100) ** 2 for v in vals) if total else 0
            if hhi > 3500:
                market_struct = "highly concentrated market structure (HHI > 3,500) — significant dependency on top segment"
            elif hhi > 1500:
                market_struct = "moderately concentrated structure — healthy but top-heavy"
            else:
                market_struct = "competitive, diversified structure (HHI < 1,500)"

            return (
                f"{dominance}. Top 2 segments together account for {top2_pct}% of total. "
                f"This reflects a {market_struct}. "
                f"{len(lbls)} segments in total; smallest is '{lbls[-1]}' at {round(vals[-1]/total*100,1)}%."
            )

        # ── BOX PLOT ─────────────────────────────────────────────────
        elif chart_type == 'box':
            import statistics
            # Try to get y values from traces first, then fall back to DataFrame
            all_y = []
            for t in traces:
                all_y.extend(_safe_nums(t.get('y')))

            # If trace has no embedded data, extract from DataFrame using layout axes
            if not all_y and df is not None:
                try:
                    y_title = layout.get('yaxis', {}).get('title', {})
                    y_col = y_title.get('text', '') if isinstance(y_title, dict) else str(y_title or '')
                    if y_col and y_col in df.columns:
                        all_y = [v for v in df[y_col].dropna().tolist() if isinstance(v, (int, float))]
                except Exception:
                    pass

            if not all_y:
                # Last resort: find first numeric column from df
                if df is not None:
                    fallback_num = [c for c in df.columns if is_numeric_dtype(df[c])]
                    if fallback_num:
                        all_y = df[fallback_num[0]].dropna().tolist()

            if not all_y:
                return "Box plot showing value spread across categories."

            median_v = statistics.median(all_y)
            sorted_y = sorted(all_y)
            n = len(sorted_y)
            q1 = sorted_y[n // 4]
            q3 = sorted_y[3 * n // 4]
            iqr = q3 - q1
            outlier_threshold = q3 + 1.5 * iqr
            lower_threshold = q1 - 1.5 * iqr
            outliers = [v for v in all_y if v > outlier_threshold or v < lower_threshold]
            pct_outliers = round(len(outliers) / n * 100, 1) if n else 0

            spread = ("tightly clustered — consistent, predictable values" if iqr < median_v * 0.2
                      else "moderately spread" if iqr < median_v * 0.8
                      else "widely dispersed — high variance suggests heterogeneous records")
            outlier_note = (
                f" {len(outliers):,} outlier{'s' if len(outliers) != 1 else ''} detected "
                f"({pct_outliers}% of records) — these extreme values merit investigation for data quality or exceptional cases."
                if outliers else
                " No significant outliers — distribution is statistically well-behaved."
            )
            return (
                f"Across {n:,} records, values are {spread}. "
                f"Median: {_fmt(median_v)} | Q1: {_fmt(q1)} | Q3: {_fmt(q3)} | IQR: {_fmt(iqr)}. "
                f"The middle 50% of values span a {round(iqr / median_v * 100) if median_v else '?'}% range around the median.{outlier_note}"
            )

        # ── CORRELATION HEATMAP ───────────────────────────────────────
        elif chart_type == 'heatmap':
            z_vals = _safe_list(trace.get('z'))
            x_labels = _safe_list(trace.get('x'))
            y_labels = _safe_list(trace.get('y'))
            strong_pos, strong_neg = [], []
            for i, row in enumerate(z_vals):
                for j, val in enumerate(row):
                    if i >= j:
                        continue
                    try:
                        v = float(val)
                        pair = f"{y_labels[i]} ↔ {x_labels[j]}"
                        if v >= 0.7:
                            strong_pos.append((pair, v))
                        elif v <= -0.7:
                            strong_neg.append((pair, v))
                    except Exception:
                        pass
            parts = [f"Correlation matrix across {len(x_labels)} numeric dimensions."]
            if strong_pos:
                top = sorted(strong_pos, key=lambda x: x[1], reverse=True)[:2]
                parts.append(
                    f"Strong positive correlations: {'; '.join(f'{p} (r={v:.2f})' for p, v in top)}."
                )
            if strong_neg:
                top = sorted(strong_neg, key=lambda x: x[1])[:2]
                parts.append(
                    f"Strong inverse relationships: {'; '.join(f'{p} (r={v:.2f})' for p, v in top)}."
                )
            if not strong_pos and not strong_neg:
                parts.append("No strong linear correlations detected (all |r| < 0.7) — variables appear largely independent.")
            return " ".join(parts)

        # ── FUNNEL ───────────────────────────────────────────────────
        elif chart_type == 'funnel':
            x_vals = _safe_nums(trace.get('x'))
            y_vals = _safe_list(trace.get('y'))
            if not x_vals or not y_vals:
                return ""
            drop_pct = round((x_vals[0] - x_vals[-1]) / x_vals[0] * 100, 1) if x_vals[0] else 0
            biggest_drop_idx = max(range(1, len(x_vals)), key=lambda i: x_vals[i-1] - x_vals[i]) if len(x_vals) > 1 else 0
            biggest_drop = round((x_vals[biggest_drop_idx-1] - x_vals[biggest_drop_idx]) / x_vals[biggest_drop_idx-1] * 100, 1) \
                           if biggest_drop_idx and x_vals[biggest_drop_idx-1] else 0
            return (
                f"'{y_vals[0]}' leads with {_fmt(x_vals[0])} — overall drop-off from top to bottom is {drop_pct}%. "
                f"Steepest fall-off occurs between '{y_vals[biggest_drop_idx-1]}' and '{y_vals[biggest_drop_idx]}' "
                f"({biggest_drop}% reduction), indicating this transition as the primary bottleneck."
                if biggest_drop_idx else
                f"'{y_vals[0]}' leads with {_fmt(x_vals[0])} across {len(y_vals)} ranked segments."
            )

        # ── TREEMAP ──────────────────────────────────────────────────
        elif chart_type == 'treemap':
            labels = _safe_list(trace.get('labels'))
            parents = _safe_list(trace.get('parents'))
            raw_vals = _safe_list(trace.get('values'))
            # Leaf nodes are those that are NOT referenced as parents
            parent_set = set(parents)
            leaf_pairs = [
                (lbl, v) for lbl, par, v in zip(labels, parents, raw_vals)
                if lbl not in parent_set and isinstance(v, (int, float)) and v > 0
            ]
            if leaf_pairs:
                leaf_pairs.sort(key=lambda x: x[1], reverse=True)
                total = sum(v for _, v in leaf_pairs)
                top_lbl, top_v = leaf_pairs[0]
                top_pct = round(top_v / total * 100, 1) if total else 0
                n80 = _pareto_cutoff([v for _, v in leaf_pairs])
                return (
                    f"Hierarchical breakdown across {len(leaf_pairs)} leaf segments. "
                    f"'{top_lbl}' is the single largest contributor at {_fmt(top_v)} ({top_pct}% of total {_fmt(total)}). "
                    f"Top {n80} segment{'s' if n80 != 1 else ''} account for ~80% of total value — "
                    f"tile size is proportional to value, instantly surfacing dominant categories."
                )
            return "Treemap showing hierarchical value distribution — tile area is proportional to contribution."

        # ── LINE / TIME-SERIES (scatter with mode=lines) ─────────────
        elif chart_type == 'scatter' and 'lines' in trace.get('mode', 'markers'):
            y_vals = _safe_nums(trace.get('y'))
            x_vals = _safe_list(trace.get('x'))
            if y_vals and len(y_vals) >= 2:
                n = len(y_vals)
                first_v, last_v = y_vals[0], y_vals[-1]
                pct_change = round((last_v - first_v) / first_v * 100, 1) if first_v else 0
                direction = "upward" if pct_change > 0 else "downward" if pct_change < 0 else "flat"
                trend_str = f"{'gained' if pct_change > 0 else 'declined'} {abs(pct_change)}%"
                peak_v = max(y_vals)
                trough_v = min(y_vals)
                peak_idx = y_vals.index(peak_v)
                peak_label = x_vals[peak_idx] if x_vals and peak_idx < len(x_vals) else f"period {peak_idx+1}"
                volatility = round((peak_v - trough_v) / ((peak_v + trough_v) / 2) * 100, 1) if (peak_v + trough_v) else 0
                if n >= 6:
                    first_half_avg = sum(y_vals[:n//2]) / (n//2)
                    second_half_avg = sum(y_vals[n//2:]) / (n - n//2)
                    momentum = round((second_half_avg - first_half_avg) / first_half_avg * 100, 1) if first_half_avg else 0
                    momentum_str = (
                        f" Momentum is {'accelerating' if momentum > 5 else 'decelerating' if momentum < -5 else 'stable'} "
                        f"— second half averaged {_fmt(second_half_avg)} vs {_fmt(first_half_avg)} in the first half."
                    )
                else:
                    momentum_str = ""
                return (
                    f"The series shows a {direction} trend, having {trend_str} from {_fmt(first_v)} to {_fmt(last_v)} "
                    f"across {n} periods. Peak value of {_fmt(peak_v)} was recorded at '{peak_label}', "
                    f"with overall volatility of {volatility}% (peak-to-trough range).{momentum_str}"
                )

        # ── SCATTER ──────────────────────────────────────────────────
        elif chart_type == 'scatter':
            x_vals = _safe_nums(trace.get('x'))
            y_vals = _safe_nums(trace.get('y'))
            if x_vals and y_vals and len(x_vals) == len(y_vals):
                n = len(x_vals)
                # Pearson r
                mx, my = sum(x_vals)/n, sum(y_vals)/n
                num = sum((x-mx)*(y-my) for x, y in zip(x_vals, y_vals))
                den = (sum((x-mx)**2 for x in x_vals) * sum((y-my)**2 for y in y_vals)) ** 0.5
                r = round(num/den, 2) if den else 0
                strength = "strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4 else "weak"
                direction = "positive" if r > 0 else "negative"
                return (
                    f"{_fmt(n)} data points plotted — Pearson r = {r} indicating a {strength} {direction} "
                    f"linear relationship. "
                    + (f"As one variable increases, the other tends to {'increase' if r > 0 else 'decrease'} proportionally."
                       if abs(r) >= 0.4 else
                       "The low correlation suggests these variables move largely independently.")
                )

    except Exception as e:
        print(f"[WARN] _describe_figure failed for {chart_type}: {e}")

    return f"Visualization: {title_text}" if title_text else ""


_TEMPORAL_TOKENS = _re.compile(
    r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec'
    r'|\d{4}[-/]\d{1,2}|\d{4}-\d{2}-\d{2}|q[1-4][-\s]\d{4}'
    r'|fy\d{2}|\d{2}-[a-z]{3}-\d{2})',
    _re.IGNORECASE,
)


def _is_temporal_x(x_vals: list) -> bool:
    """Return True when the first few X-axis labels look like time periods."""
    if not x_vals or len(x_vals) < 2:
        return False
    matches = sum(1 for v in x_vals[:5] if _TEMPORAL_TOKENS.match(str(v).strip()))
    return matches >= min(2, len(x_vals))


def _extract_chart_data_text(fig_dict: dict, max_rows: int = 15) -> str:
    """Return the chart's aggregated data as a short text block for the LLM prompt."""
    if not fig_dict or 'data' not in fig_dict:
        return ""
    traces = fig_dict.get('data', [])
    if not traces:
        return ""
    trace = traces[0]
    chart_type = trace.get('type', '')

    try:
        if chart_type == 'bar':
            x_vals = _safe_list(trace.get('x'))
            y_vals = _safe_nums(trace.get('y'))
            if x_vals and y_vals:
                pairs = list(zip(x_vals, y_vals))[:max_rows]
                return "\n".join(f"  {x}: {_fmt(y)}" for x, y in pairs)

        elif chart_type == 'pie':
            labels = _safe_list(trace.get('labels'))
            values = _safe_nums(trace.get('values'))
            if labels and values:
                total = sum(values) or 1
                pairs = sorted(zip(labels, values), key=lambda p: p[1], reverse=True)[:max_rows]
                return "\n".join(f"  {lbl}: {_fmt(v)} ({round(v / total * 100, 1)}%)"
                                 for lbl, v in pairs)

        elif chart_type == 'scatter':
            x_vals = _safe_list(trace.get('x'))
            y_vals = _safe_nums(trace.get('y'))
            if x_vals and y_vals:
                pairs = list(zip(x_vals, y_vals))[:max_rows]
                return "\n".join(f"  {x}: {_fmt(y)}" for x, y in pairs)

        elif chart_type == 'heatmap':
            return "(correlation matrix — see chart for values)"

    except Exception:
        pass
    return ""


def register_dashboard_callbacks(app, get_cached_df=None, chart_analyzer=None):
    """Register all dashboard-related callbacks

    Args:
        app: Dash app instance
        get_cached_df: Function to load cached dataframe (avoids dcc.Store issues)
    """

    # Callback to update KPIs based on filters
    @app.callback(
        Output('kpi-cards-container', 'children'),
        [Input({'type': 'filter-dropdown', 'index': ALL}, 'value')],
        [State('store-kpi-selections-dashboard', 'data'),
         State('store-filter-selections-dashboard', 'data'),
         State('store-confirmed-dtypes-dashboard', 'data')],
        prevent_initial_call=False
    )
    def update_kpi_on_filter(filter_values, kpi_selections, filter_selections, confirmed_dtypes):
        """Update all KPI cards when filters change"""
        print(f"\n[DEBUG] update_kpi_on_filter called")

        if not kpi_selections:
            print(f"[DEBUG] PreventUpdate: no kpi_selections")
            raise dash.exceptions.PreventUpdate

        try:
            # Load DataFrame from cache file instead of dcc.Store (avoids serialization issues)
            if get_cached_df:
                df = get_cached_df()
                if df is None:
                    return html.Div("Error: Could not load cached data", style={'color': '#DC2626', 'padding': '15px'})
            else:
                return html.Div("Error: Data loading not configured", style={'color': '#DC2626', 'padding': '15px'})

            print(f"[DEBUG] DataFrame loaded from cache: {df.shape[0]} rows x {df.shape[1]} cols")

            # Apply filters to dataframe
            filtered_df = df.copy()
            if filter_selections and filter_values:
                for filter_sel, filter_value in zip(filter_selections, filter_values):
                    col = filter_sel['column']
                    if filter_value and filter_value != "All" and col in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[col] == filter_value]

            # Generate cards for all KPIs
            kpi_cards = []

            # Defensive check for kpi_selections format
            if not isinstance(kpi_selections, list):
                print(f"[ERROR] kpi_selections is not a list: type={type(kpi_selections)}")
                return html.Div("Invalid KPI selections format", style={'color': '#DC2626', 'padding': '15px'})

            for kpi in kpi_selections:
                if not isinstance(kpi, dict):
                    print(f"[ERROR] KPI item is not a dict: type={type(kpi)}, value={str(kpi)[:100]}")
                    continue

                raw_col = kpi.get('column', '')
                agg = kpi.get('aggregation', 'sum')
                label = kpi.get('label', raw_col)

                # Fuzzy-match column name (handles LLM returning "Sum of Amount" etc.)
                col = Formatter.resolve_column(raw_col, filtered_df.columns)

                if not col or col not in filtered_df.columns:
                    print(f"[WARN] KPI column '{raw_col}' not found (resolved: '{col}')")
                    kpi_cards.append(html.Div([
                        html.Div(label, style={'fontSize': '12px', 'color': TEXT_LIGHT, 'fontWeight': 'bold'}),
                        html.Div("N/A", style={'fontSize': '18px', 'color': '#DC2626', 'marginTop': '8px'}),
                        html.Div(f"Column not found: {raw_col}", style={'fontSize': '10px', 'color': '#DC2626', 'marginTop': '4px'}),
                    ], style={'background': '#FEE2E2', 'padding': '15px', 'borderRadius': '6px', 'flex': '1', 'minWidth': '200px'}))
                    continue

                # Coerce string-encoded numerics before aggregating
                series = Formatter.coerce_numeric_series(filtered_df[col])

                # Calculate aggregated value
                try:
                    if agg == 'sum':
                        value = series.sum()
                    elif agg == 'mean':
                        value = series.mean()
                    elif agg == 'count':
                        value = series.count()
                    elif agg == 'max':
                        value = series.max()
                    elif agg == 'min':
                        value = series.min()
                    else:
                        value = series.iloc[0] if len(series) > 0 else None

                    if isinstance(value, str):
                        value = None  # string-concat from non-coercible column

                    print(f"[DEBUG] KPI '{col}' ({agg}): {value} (type={type(value).__name__})")
                except Exception as calc_err:
                    print(f"[ERROR] Failed to calculate '{col}' ({agg}): {type(calc_err).__name__}: {str(calc_err)[:100]}")
                    value = None

                # Format the value
                dtype = confirmed_dtypes.get(col, 'categorical') if confirmed_dtypes else 'categorical'
                formatted_value = Formatter.format_kpi_value(value, dtype, agg)
                print(f"[DEBUG] KPI {col} formatted: {formatted_value}")

                kpi_cards.append(html.Div([
                    html.Div(label, style={'fontSize': '12px', 'color': TEXT_LIGHT, 'fontWeight': 'bold'}),
                    html.Div(formatted_value, style={'fontSize': '24px', 'fontWeight': 'bold', 'color': PRIMARY, 'marginTop': '8px'}),
                    html.Div(f"({agg})", style={'fontSize': '11px', 'color': TEXT_LIGHT, 'marginTop': '5px'}),
                ], style={'background': '#F9FAFB', 'padding': '15px', 'borderRadius': '6px', 'border': f'1px solid {BORDER}', 'flex': '1', 'minWidth': '200px'}))

            return html.Div(kpi_cards, style={'display': 'flex', 'gap': '15px', 'flexWrap': 'wrap'})

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)[:50]}"
            print(f"[ERROR] KPI callback failed: {error_msg}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return html.Div(f"KPI Error: {error_msg}", style={'color': '#DC2626', 'padding': '15px'})


    # Callback to render charts - uses AI suggestions when available, else auto-generates
    @app.callback(
        Output('charts-container', 'children'),
        [Input({'type': 'filter-dropdown', 'index': ALL}, 'value')],
        [State('store-filter-selections-dashboard', 'data'),
         State('store-ai-suggestions', 'data')],
        prevent_initial_call=False
    )
    def update_charts(filter_values, filter_selections, ai_suggestions):
        """Render AI-suggested charts when available, else auto-generate from data."""
        import plotly.graph_objects as go

        try:
            if not get_cached_df:
                return html.Div("Error: Data loading not configured")

            df = get_cached_df()
            if df is None:
                return html.Div("Error: Could not load cached data", style={'color': '#DC2626'})

            # Apply filters
            filtered_df = df.copy()
            if filter_selections and filter_values:
                for filter_sel, filter_value in zip(filter_selections, filter_values):
                    col = filter_sel.get('column', '')
                    if filter_value and filter_value != "All" and col in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[col].astype(str) == str(filter_value)]

            print(f"[CHARTS] Generating charts for {len(filtered_df):,} rows")

            # Safety coercion pass — handles pandas 3.0 StringDtype columns
            # (dtype prints as 'str' not 'object', so we use not is_numeric_dtype).
            filtered_df = filtered_df.copy()
            for col in list(filtered_df.columns):
                if not is_numeric_dtype(filtered_df[col]):
                    try:
                        cleaned = filtered_df[col].astype(str).str.replace(r'[,₹$€£]', '', regex=True).str.strip()
                        converted = pd.to_numeric(cleaned, errors='coerce')
                        if converted.notna().sum() / max(len(filtered_df), 1) > 0.5:
                            filtered_df[col] = converted
                    except Exception:
                        pass

            # Classify columns
            cat_cols = [c for c in filtered_df.columns
                        if (filtered_df[c].dtype == 'object' or is_string_dtype(filtered_df[c]))
                        and 2 <= filtered_df[c].nunique() <= 50]
            n_rows = len(filtered_df)
            # Cardinality threshold: relaxed for small filtered sets (avoid excluding
            # continuous metrics like Amount when only a few hundred rows remain)
            card_thresh = 0.95 if n_rows < 5000 else 0.8
            num_cols = [c for c in filtered_df.columns
                        if is_numeric_dtype(filtered_df[c])
                        and filtered_df[c].nunique() > 1
                        and filtered_df[c].notna().sum() > 0
                        and not c.startswith('Unnamed')
                        and (filtered_df[c].nunique() / n_rows) < card_thresh]

            print(f"[CHARTS] Found {len(cat_cols)} categorical, {len(num_cols)} numeric columns")

            chart_divs = []
            pending_charts = []  # (fig, label, x_col, y_col, chart_type)

            CHART_STYLE = {
                'background': '#FFFFFF',
                'borderRadius': '8px',
                'padding': '4px',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.08)',
            }
            LAYOUT_ARGS = dict(
                height=400,
                margin=dict(l=60, r=30, t=70, b=80),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#FAFBFC',
                font=dict(color='#1A1F2E', size=11),
                title_font=dict(size=15, color='#1A365D', family='Arial, sans-serif'),
                showlegend=True,
                legend=dict(
                    x=0.01, y=0.99,
                    bgcolor='rgba(255, 255, 255, 0.8)',
                    bordercolor='#E5E7EB',
                    borderwidth=1,
                    font=dict(size=10)
                ),
                hovermode='x unified',
                xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#F0F0F0'),
                yaxis=dict(showgrid=True, gridwidth=1, gridcolor='#F0F0F0'),
                clickmode='event+select',  # Enable click events
            )

            def make_card(fig, label, chart_index=0, precomputed_insight=None):
                fig.update_layout(**LAYOUT_ARGS)
                fig_dict = fig.to_dict() if hasattr(fig, 'to_dict') else fig
                insight = precomputed_insight if precomputed_insight is not None else _describe_figure(fig_dict, filtered_df)
                insight_el = html.Div([
                    html.Div([
                        html.Span("ANALYST INSIGHT", style={
                            'fontSize': '9px', 'fontWeight': '800',
                            'textTransform': 'uppercase', 'letterSpacing': '0.12em',
                            'backgroundColor': '#1A365D', 'color': 'white',
                            'padding': '3px 10px', 'borderRadius': '3px',
                            'marginRight': '12px', 'flexShrink': '0',
                        }),
                        html.Span(insight or "—", style={
                            'color': '#1A1F2E', 'fontSize': '12px', 'lineHeight': '1.75',
                            'fontStyle': 'normal',
                        }),
                    ], style={
                        'display': 'flex', 'alignItems': 'flex-start', 'gap': '4px',
                    }),
                ], style={
                    'padding': '12px 16px',
                    'borderTop': '1px solid #E2E8F0',
                    'borderLeft': '4px solid #1A365D',
                    'backgroundColor': '#F8FAFF',
                    'borderRadius': '0 0 8px 8px',
                    'margin': '0',
                }) if insight else html.Div(style={'display': 'none'})

                return html.Div([
                    dcc.Graph(
                        id={'type': 'chart-graph', 'index': chart_index},
                        figure=fig,
                        config={'displayModeBar': False},
                        style={'marginBottom': '0'}
                    ),
                    # Static description — no callback needed, generated inline
                    html.Div(
                        id={'type': 'chart-description', 'index': chart_index},
                        children=insight_el,
                    ),
                ], style=CHART_STYLE)

            def _gen_insight(item):
                """Generate data-grounded insight from actual Plotly trace values.

                Uses _describe_figure (rule-based, always accurate) rather than
                the LLM, which tends to hallucinate names and values for chart
                narration tasks despite strict prompts.
                """
                fig_, label_, x_col_, y_col_, ct_ = item
                fig_dict_ = fig_.to_dict() if hasattr(fig_, 'to_dict') else fig_
                return _describe_figure(fig_dict_, filtered_df)

            # ── AI-SUGGESTED CHARTS (when store-ai-suggestions is populated) ──
            ai_chart_specs = (ai_suggestions or {}).get('charts', [])
            if ai_chart_specs:
                print(f"[CHARTS] Rendering {len(ai_chart_specs)} AI-suggested charts")
                for spec in ai_chart_specs:
                    try:
                        ct   = (spec.get('type') or 'bar').lower()
                        x_c  = spec.get('x', '')
                        y_c  = spec.get('y', '')
                        ttl  = spec.get('title', f'{ct}: {x_c}')

                        # Resolve SQL-style column names the LLM sometimes returns
                        # e.g. "count(*)", "COUNT(id)", "sum(Amount)" → clear y_c so
                        # chart falls back to count-based rendering
                        if y_c and y_c not in filtered_df.columns:
                            y_lower = y_c.lower()
                            if any(kw in y_lower for kw in ('count', 'sum(', 'avg(', 'max(', 'min(')):
                                # Try to extract the column name from "sum(Amount)" → "Amount"
                                inner = _re.sub(r'\w+\((.+)\)', r'\1', y_c).strip()
                                if inner in filtered_df.columns:
                                    y_c = inner
                                else:
                                    y_c = ''  # fall back to count-based chart
                            else:
                                y_c = ''  # unknown column → count-based

                        # Validate x column exists
                        if x_c and x_c not in filtered_df.columns:
                            print(f"[AI CHART] x-col '{x_c}' not in dataframe, skipping")
                            continue

                        fig = None

                        if ct == 'bar':
                            if y_c and y_c in filtered_df.columns and is_numeric_dtype(filtered_df[y_c]):
                                agg = filtered_df.groupby(x_c)[y_c].sum().reset_index().nlargest(15, y_c)
                                fig = px.bar(agg, x=x_c, y=y_c, title=ttl, color=y_c, color_continuous_scale='Blues')
                                fig.update_coloraxes(showscale=False)
                            else:
                                vc = filtered_df[x_c].value_counts().head(15).reset_index()
                                vc.columns = [x_c, 'Count']
                                fig = px.bar(vc, x=x_c, y='Count', title=ttl, color='Count', color_continuous_scale='Blues')
                                fig.update_coloraxes(showscale=False)

                        elif ct == 'pie':
                            if y_c and y_c in filtered_df.columns and is_numeric_dtype(filtered_df[y_c]):
                                agg = filtered_df.groupby(x_c)[y_c].sum().nlargest(8)
                                fig = px.pie(values=agg.values, names=agg.index, title=ttl, hole=0.35,
                                             color_discrete_sequence=px.colors.qualitative.Set2)
                            else:
                                vc = filtered_df[x_c].value_counts().head(8)
                                fig = px.pie(values=vc.values, names=vc.index, title=ttl, hole=0.35,
                                             color_discrete_sequence=px.colors.qualitative.Set2)

                        elif ct == 'line':
                            _has_numeric_y = y_c and y_c in filtered_df.columns and is_numeric_dtype(filtered_df[y_c])
                            try:
                                cols = [x_c] if not _has_numeric_y else [x_c, y_c]
                                line_df = filtered_df[cols].dropna(subset=[x_c]).copy()

                                # Robust date parsing: try specific format first, then mixed with utc
                                raw_x = line_df[x_c]
                                parsed = None
                                for fmt in ('%d-%b-%y', '%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y', None):
                                    try:
                                        if fmt:
                                            p = pd.to_datetime(raw_x, format=fmt, errors='coerce')
                                        else:
                                            p = pd.to_datetime(raw_x, format='mixed', dayfirst=True,
                                                               errors='coerce', utc=True)
                                            p = p.dt.tz_convert(None)  # strip timezone
                                        if p.notna().sum() > len(raw_x) * 0.5:
                                            parsed = p
                                            break
                                    except Exception:
                                        continue

                                if parsed is not None:
                                    line_df[x_c] = parsed
                                    line_df = line_df.dropna(subset=[x_c]).sort_values(x_c)
                                    line_df[x_c] = line_df[x_c].dt.to_period('M').dt.to_timestamp()

                                if _has_numeric_y:
                                    agg = line_df.groupby(x_c)[y_c].sum().reset_index()
                                    y_label = y_c
                                else:
                                    agg = line_df.groupby(x_c).size().reset_index(name='Count')
                                    y_label = 'Count'
                                fig = px.line(agg, x=x_c, y=y_label, title=ttl,
                                              markers=True, color_discrete_sequence=['#1A365D'])
                            except Exception as ex:
                                print(f"[AI CHART] Line chart error: {ex}")

                        elif ct == 'histogram':
                            col_h = y_c if (y_c and y_c in filtered_df.columns) else x_c
                            if col_h in filtered_df.columns and is_numeric_dtype(filtered_df[col_h]):
                                fig = px.histogram(filtered_df, x=col_h, nbins=30, title=ttl,
                                                   color_discrete_sequence=['#1A365D'])

                        elif ct == 'box':
                            if y_c and y_c in filtered_df.columns and is_numeric_dtype(filtered_df[y_c]):
                                top_cats = filtered_df[x_c].value_counts().head(10).index
                                box_df = filtered_df[filtered_df[x_c].isin(top_cats)]
                                fig = px.box(box_df, x=x_c, y=y_c, title=ttl,
                                             color=x_c, color_discrete_sequence=px.colors.qualitative.Set2)
                                fig.update_layout(showlegend=False)

                        elif ct == 'scatter':
                            if (x_c in filtered_df.columns and y_c and y_c in filtered_df.columns
                                    and is_numeric_dtype(filtered_df[x_c])
                                    and is_numeric_dtype(filtered_df[y_c])):
                                fig = px.scatter(filtered_df.sample(min(2000, len(filtered_df))),
                                                 x=x_c, y=y_c, title=ttl,
                                                 color_discrete_sequence=['#1A365D'], opacity=0.6)

                        elif ct == 'funnel':
                            if y_c and y_c in filtered_df.columns and is_numeric_dtype(filtered_df[y_c]):
                                fd = filtered_df.groupby(x_c)[y_c].sum().nlargest(8).reset_index()
                                fig = px.funnel(fd, x=y_c, y=x_c, title=ttl,
                                                color_discrete_sequence=['#1A365D'])

                        elif ct == 'treemap':
                            if y_c and y_c in filtered_df.columns and is_numeric_dtype(filtered_df[y_c]):
                                # Look for a second categorical to nest under
                                second_cat = next((c for c in cat_cols if c != x_c), None)
                                if second_cat:
                                    td = filtered_df.groupby([x_c, second_cat])[y_c].sum().reset_index()
                                    td = td[td[y_c] > 0]
                                    fig = px.treemap(td, path=[x_c, second_cat], values=y_c, title=ttl,
                                                     color=y_c, color_continuous_scale='Blues')
                                else:
                                    td = filtered_df.groupby(x_c)[y_c].sum().reset_index()
                                    td = td[td[y_c] > 0]
                                    fig = px.treemap(td, path=[x_c], values=y_c, title=ttl,
                                                     color=y_c, color_continuous_scale='Blues')
                                fig.update_layout(height=420)

                        elif ct == 'heatmap':
                            # Recompute locally — num_cols may be restricted by cardinality filter
                            local_num = [c for c in filtered_df.columns
                                         if is_numeric_dtype(filtered_df[c])
                                         and filtered_df[c].nunique() > 1
                                         and not c.startswith('Unnamed')]
                            if len(local_num) >= 2:
                                corr = filtered_df[local_num[:8]].corr().round(2)
                                fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r',
                                                zmin=-1, zmax=1, title=ttl)
                                fig.update_layout(height=420)

                        if fig is not None:
                            pending_charts.append((fig, ttl, x_c, y_c, ct))
                            print(f"[AI CHART] Built: {ttl}")
                        else:
                            print(f"[AI CHART] Could not render '{ttl}' (type={ct}, x={x_c}, y={y_c})")
                    except Exception as e:
                        print(f"[AI CHART] Error rendering '{spec.get('title', '')}': {e}")

                # After AI charts, add 2 standard auto-charts if data permits
                if cat_cols and not any(s.get('type') == 'pie' for s in ai_chart_specs):
                    try:
                        col = cat_cols[0]
                        vc = filtered_df[col].value_counts().head(8)
                        fig = px.pie(values=vc.values, names=vc.index, title=f"Share by {col}",
                                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.35)
                        pending_charts.append((fig, f"pie_{col}", col, 'Count', 'pie'))
                    except Exception:
                        pass
                if len(num_cols) >= 3 and not any(s.get('type') == 'heatmap' for s in ai_chart_specs):
                    try:
                        corr = filtered_df[num_cols[:8]].corr().round(2)
                        fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r',
                                        zmin=-1, zmax=1, title="Correlation Matrix")
                        fig.update_layout(height=420)
                        pending_charts.append((fig, "correlation", '', '', 'heatmap'))
                    except Exception:
                        pass

            else:
                # ── NO AI SUGGESTIONS — full auto-generation ─────────────────

                # ── 1. Categorical distributions (bar: top 15) ───────────────
                for col in cat_cols[:5]:
                    try:
                        vc = filtered_df[col].value_counts().head(15).reset_index()
                        vc.columns = [col, 'Count']
                        fig = px.bar(vc, x=col, y='Count',
                                     title=f"Distribution: {col}",
                                     color='Count', color_continuous_scale='Blues')
                        fig.update_coloraxes(showscale=False)
                        pending_charts.append((fig, col, col, 'Count', 'bar'))
                        print(f"[CHARTS] Added categorical bar: {col}")
                    except Exception as e:
                        print(f"[CHARTS] Error categorical {col}: {e}")

                # ── 2. Numeric histograms ─────────────────────────────────────
                for col in num_cols[:3]:
                    try:
                        fig = px.histogram(filtered_df, x=col, nbins=30,
                                           title=f"Distribution: {col}",
                                           color_discrete_sequence=['#1A365D'])
                        pending_charts.append((fig, col, col, col, 'histogram'))
                        print(f"[CHARTS] Added histogram: {col}")
                    except Exception as e:
                        print(f"[CHARTS] Error histogram {col}: {e}")

                # ── 3. Numeric by categorical (bar aggregation) ───────────────
                if cat_cols and num_cols:
                    for num_col in num_cols[:2]:
                        for cat_col in cat_cols[:2]:
                            try:
                                agg = filtered_df.groupby(cat_col)[num_col].sum().reset_index()
                                agg = agg.nlargest(15, num_col)
                                fig = px.bar(agg, x=cat_col, y=num_col,
                                             title=f"Total {num_col} by {cat_col}",
                                             color=num_col, color_continuous_scale='Teal')
                                fig.update_coloraxes(showscale=False)
                                pending_charts.append((fig, f"{num_col}_by_{cat_col}", cat_col, num_col, 'bar'))
                                print(f"[CHARTS] Added agg bar: {num_col} by {cat_col}")
                            except Exception as e:
                                print(f"[CHARTS] Error agg {num_col} by {cat_col}: {e}")

                # ── 4. Box plot ───────────────────────────────────────────────
                if cat_cols and num_cols:
                    try:
                        cat, num = cat_cols[0], num_cols[0]
                        top_cats = filtered_df[cat].value_counts().head(10).index
                        box_df = filtered_df[filtered_df[cat].isin(top_cats)]
                        fig = px.box(box_df, x=cat, y=num,
                                     title=f"{num} Distribution by {cat}",
                                     color=cat, color_discrete_sequence=px.colors.qualitative.Set2)
                        fig.update_layout(showlegend=False)
                        pending_charts.append((fig, f"box_{cat}_{num}", cat, num, 'box'))
                        print(f"[CHARTS] Added box plot: {num} by {cat}")
                    except Exception as e:
                        print(f"[CHARTS] Error box plot: {e}")

                # ── 5. Pie chart ──────────────────────────────────────────────
                if cat_cols:
                    try:
                        col = cat_cols[0]
                        vc = filtered_df[col].value_counts().head(8)
                        fig = px.pie(values=vc.values, names=vc.index,
                                     title=f"Share by {col}",
                                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.35)
                        pending_charts.append((fig, f"pie_{col}", col, 'Count', 'pie'))
                        print(f"[CHARTS] Added pie: {col}")
                    except Exception as e:
                        print(f"[CHARTS] Error pie: {e}")

                # ── 6. Correlation heatmap (≥3 numeric) ───────────────────────
                if len(num_cols) >= 3:
                    try:
                        corr = filtered_df[num_cols[:8]].corr().round(2)
                        fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r',
                                        zmin=-1, zmax=1, title="Correlation Matrix")
                        fig.update_layout(height=420)
                        pending_charts.append((fig, "correlation", '', '', 'heatmap'))
                        print(f"[CHARTS] Added correlation heatmap")
                    except Exception as e:
                        print(f"[CHARTS] Error heatmap: {e}")

                # ── 7. Funnel ─────────────────────────────────────────────────
                if cat_cols and num_cols:
                    try:
                        cat, num = cat_cols[0], num_cols[0]
                        funnel_data = filtered_df.groupby(cat)[num].sum().nlargest(8).reset_index()
                        fig = px.funnel(funnel_data, x=num, y=cat,
                                        title=f"Top {cat} by {num} (Funnel)",
                                        color_discrete_sequence=['#1A365D'])
                        pending_charts.append((fig, f"funnel_{cat}", cat, num, 'funnel'))
                        print(f"[CHARTS] Added funnel: {cat} by {num}")
                    except Exception as e:
                        print(f"[CHARTS] Error funnel: {e}")

                # ── 8. Treemap ────────────────────────────────────────────────
                if len(cat_cols) >= 2 and num_cols:
                    try:
                        cat1, cat2, num = cat_cols[0], cat_cols[1], num_cols[0]
                        tree_df = filtered_df.groupby([cat1, cat2])[num].sum().reset_index()
                        tree_df = tree_df[tree_df[num] > 0]
                        fig = px.treemap(tree_df, path=[cat1, cat2], values=num,
                                         title=f"{num} Breakdown: {cat1} > {cat2}",
                                         color=num, color_continuous_scale='Blues')
                        fig.update_layout(height=420)
                        pending_charts.append((fig, "treemap", cat1, num, 'treemap'))
                        print(f"[CHARTS] Added treemap")
                    except Exception as e:
                        print(f"[CHARTS] Error treemap: {e}")

            print(f"[CHARTS] Built {len(pending_charts)} charts — generating insights...")

            if not pending_charts:
                return html.Div("No charts could be generated for this data.",
                                style={'color': '#6B7280', 'padding': '20px', 'textAlign': 'center'})

            # ── Batch-generate insights in parallel (LLM or stats fallback) ──
            n_workers = min(8, len(pending_charts))
            try:
                with ThreadPoolExecutor(max_workers=n_workers) as ex:
                    insights = list(ex.map(_gen_insight, pending_charts, timeout=45))
            except Exception as _te:
                print(f"[WARN] Parallel insight generation error: {_te} — falling back to stats")
                insights = [_gen_insight(item) for item in pending_charts]

            for i, (item, insight) in enumerate(zip(pending_charts, insights)):
                fig_, label_ = item[0], item[1]
                chart_divs.append(make_card(fig_, label_, i, precomputed_insight=insight))

            print(f"[CHARTS] Total charts rendered: {len(chart_divs)}")
            return chart_divs

        except Exception as e:
            import traceback
            print(f"[ERROR] update_charts: {e}\n{traceback.format_exc()}")
            return html.Div(f"Error rendering charts: {str(e)}", style={'color': '#DC2626'})

    # ═══════════════════════════════════════════════════════════════
    # FILE UPLOAD CALLBACKS
    # ═══════════════════════════════════════════════════════════════

    @app.callback(
        Output('upload-status', 'children'),
        Output('preview-container', 'children'),
        Input('upload-data', 'contents'),
        Input('upload-data', 'filename'),
        prevent_initial_call=True
    )
    def handle_file_upload(contents, filename):
        """Parse upload, run full data profiling, show analysis panel"""
        if not contents or not filename:
            return "", []

        try:
            from core.file_handler import FileHandler
            from core.data_profiler import DataProfiler
            from core.cache_manager import CacheManager
            import numpy as np

            df = FileHandler.parse_file(contents, filename)
            is_valid, error_msg = FileHandler.validate_dataframe(df)
            if not is_valid:
                return dbc.Alert(error_msg, color="danger"), []

            # Save to cache immediately — avoids large dcc.Store serialisation
            upload_id, profiles_obj = CacheManager.save_upload(df, filename)
            print(f"[OK] Upload saved: {upload_id} ({len(df):,} rows)")

            # Run full profiler for display
            profiler = DataProfiler()
            profiles = profiler.profile(df)

            # Classify columns
            numeric_cols   = [n for n, p in profiles.items() if p.dtype == 'numeric']
            categorical_cols = [n for n, p in profiles.items() if p.dtype == 'categorical']
            temporal_cols  = [n for n, p in profiles.items() if p.is_temporal]
            boolean_cols   = [n for n, p in profiles.items() if p.dtype == 'boolean']

            # Data quality
            total_cells = df.shape[0] * df.shape[1]
            missing_cells = df.isnull().sum().sum()
            completeness = round((1 - missing_cells / total_cells) * 100, 1) if total_cells else 100
            dup_rows = df.duplicated().sum()

            # Memory
            mem_mb = round(df.memory_usage(deep=True).sum() / 1024**2, 2)

            # ── STAT CARD builder ─────────────────────────────
            def stat_card(label, value, sub="", color=NAVY, bg="#EBF4FF"):
                return html.Div([
                    html.Div(str(value), style={
                        'fontSize': '26px', 'fontWeight': '800', 'color': color, 'lineHeight': '1',
                    }),
                    html.Div(label, style={
                        'fontSize': '11px', 'fontWeight': '700', 'textTransform': 'uppercase',
                        'letterSpacing': '0.07em', 'color': TEXT_LIGHT, 'marginTop': '4px',
                    }),
                    html.Div(sub, style={'fontSize': '11px', 'color': TEXT_LIGHT, 'marginTop': '2px'}) if sub else None,
                ], style={
                    'backgroundColor': bg, 'border': f'1px solid {BORDER}',
                    'borderTop': f'3px solid {color}', 'borderRadius': '6px',
                    'padding': '14px 16px', 'flex': '1', 'minWidth': '110px',
                })

            # ── COLUMN PROFILE ROW builder ────────────────────
            def profile_row(name, p, idx):
                badge_color = {
                    'numeric': '#1A365D', 'categorical': '#065F46',
                    'temporal': '#7C3AED', 'boolean': '#92400E',
                }.get(p.dtype, '#374151')
                badge_bg = {
                    'numeric': '#EBF4FF', 'categorical': '#D1FAE5',
                    'temporal': '#EDE9FE', 'boolean': '#FEF3C7',
                }.get(p.dtype, '#F3F4F6')

                top_vals = ", ".join(str(v) for v in (p.top_values or [])[:3])
                missing_pct = round(p.missing_pct, 1)
                quality_color = '#DC2626' if missing_pct > 20 else '#D97706' if missing_pct > 5 else '#16A34A'

                return html.Tr([
                    html.Td(html.Span(name, style={'fontWeight': '600', 'color': NAVY, 'fontSize': '12px'}),
                            style={'padding': '8px 12px', 'borderBottom': f'1px solid {BORDER}',
                                   'backgroundColor': '#F8FAFF' if idx % 2 == 0 else '#FFFFFF'}),
                    html.Td(html.Span(p.dtype.upper(), style={
                        'fontSize': '10px', 'fontWeight': '700', 'padding': '2px 8px',
                        'borderRadius': '10px', 'color': badge_color, 'backgroundColor': badge_bg,
                        'border': f'1px solid {badge_color}22',
                    }), style={'padding': '8px 12px', 'borderBottom': f'1px solid {BORDER}',
                               'backgroundColor': '#F8FAFF' if idx % 2 == 0 else '#FFFFFF'}),
                    html.Td(f"{p.cardinality:,}", style={
                        'padding': '8px 12px', 'fontSize': '12px', 'color': TEXT,
                        'borderBottom': f'1px solid {BORDER}',
                        'backgroundColor': '#F8FAFF' if idx % 2 == 0 else '#FFFFFF'}),
                    html.Td(html.Span(f"{missing_pct}%", style={'color': quality_color, 'fontWeight': '600', 'fontSize': '12px'}),
                            style={'padding': '8px 12px', 'borderBottom': f'1px solid {BORDER}',
                                   'backgroundColor': '#F8FAFF' if idx % 2 == 0 else '#FFFFFF'}),
                    html.Td(html.Span(top_vals or "—", style={'fontSize': '11px', 'color': TEXT_LIGHT}),
                            style={'padding': '8px 12px', 'borderBottom': f'1px solid {BORDER}',
                                   'backgroundColor': '#F8FAFF' if idx % 2 == 0 else '#FFFFFF',
                                   'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                ])

            TH_STYLE = {
                'fontSize': '10px', 'fontWeight': '700', 'textTransform': 'uppercase',
                'letterSpacing': '0.07em', 'padding': '10px 12px',
                'backgroundColor': NAVY, 'color': '#FFFFFF',
                'borderBottom': f'2px solid {GOLD}',
            }

            profile_table = html.Table([
                html.Thead(html.Tr([
                    html.Th("Column", style=TH_STYLE),
                    html.Th("Type", style=TH_STYLE),
                    html.Th("Unique Values", style=TH_STYLE),
                    html.Th("Missing", style=TH_STYLE),
                    html.Th("Top Values", style=TH_STYLE),
                ])),
                html.Tbody([
                    profile_row(name, p, idx)
                    for idx, (name, p) in enumerate(profiles.items())
                ]),
            ], style={
                'width': '100%', 'borderCollapse': 'collapse',
                'border': f'1px solid {BORDER}', 'borderRadius': '6px',
            })

            analysis_panel = html.Div([
                # ── Header ─────────────────────────────────────
                html.Div([
                    html.Div([
                        html.Span("DATA INTELLIGENCE REPORT", style={
                            'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.12em',
                            'color': GOLD, 'display': 'block', 'marginBottom': '4px',
                        }),
                        html.H3(filename, style={'color': '#FFFFFF', 'fontWeight': '700', 'margin': '0', 'fontSize': '18px'}),
                    ]),
                ], style={
                    'backgroundColor': NAVY, 'padding': '20px 24px',
                    'borderRadius': '8px 8px 0 0', 'borderBottom': f'3px solid {GOLD}',
                }),

                # ── KPI strip ──────────────────────────────────
                html.Div([
                    stat_card("Total Records", f"{len(df):,}", f"{mem_mb} MB"),
                    stat_card("Columns", f"{len(df.columns)}", f"{len(numeric_cols)} numeric"),
                    stat_card("Data Completeness", f"{completeness}%",
                              "Excellent" if completeness >= 95 else "Good" if completeness >= 80 else "Needs attention",
                              color='#16A34A' if completeness >= 95 else '#D97706' if completeness >= 80 else '#DC2626',
                              bg='#F0FDF4' if completeness >= 95 else '#FFFBEB' if completeness >= 80 else '#FEF2F2'),
                    stat_card("Categorical Cols", f"{len(categorical_cols)}", "Available as filters"),
                    stat_card("Numeric Cols", f"{len(numeric_cols)}", "Available as KPIs"),
                    stat_card("Duplicate Rows", f"{dup_rows:,}",
                              "None detected" if dup_rows == 0 else "Review recommended",
                              color='#16A34A' if dup_rows == 0 else '#D97706',
                              bg='#F0FDF4' if dup_rows == 0 else '#FFFBEB'),
                ], style={
                    'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap',
                    'padding': '16px 24px', 'backgroundColor': '#F8FAFF',
                    'borderBottom': f'1px solid {BORDER}',
                }),

                # ── Column profile table ────────────────────────
                html.Div([
                    html.Div("Column-Level Profile", style={
                        'fontSize': '13px', 'fontWeight': '700', 'color': NAVY,
                        'marginBottom': '12px', 'textTransform': 'uppercase', 'letterSpacing': '0.05em',
                    }),
                    html.Div(profile_table, style={'overflowX': 'auto'}),
                ], style={'padding': '20px 24px', 'backgroundColor': '#FFFFFF'}),

                # ── Data Preview ───────────────────────────────
                html.Div([
                    html.Div("Sample Data — First 5 Rows", style={
                        'fontSize': '13px', 'fontWeight': '700', 'color': NAVY,
                        'marginBottom': '12px', 'textTransform': 'uppercase', 'letterSpacing': '0.05em',
                    }),
                    html.Div([
                        html.Table([
                            html.Thead(html.Tr([html.Th(c, style=TH_STYLE) for c in df.columns])),
                            html.Tbody([
                                html.Tr([
                                    html.Td(str(v)[:40], style={
                                        'fontSize': '11px', 'padding': '7px 12px',
                                        'borderBottom': f'1px solid {BORDER}',
                                        'backgroundColor': '#F8FAFF' if i % 2 == 0 else '#FFFFFF',
                                        'whiteSpace': 'nowrap',
                                    })
                                    for v in row
                                ])
                                for i, row in enumerate(df.head(5).values)
                            ]),
                        ], style={'width': '100%', 'borderCollapse': 'collapse', 'border': f'1px solid {BORDER}'})
                    ], style={'overflowX': 'auto'}),
                ], style={
                    'padding': '20px 24px', 'backgroundColor': '#FAFBFC',
                    'borderTop': f'1px solid {BORDER}',
                }),

                # ── Action footer ─────────────────────────────
                html.Div([
                    html.Div([
                        html.Span(
                            f"Dataset validated — {len(df):,} rows ready for analysis",
                            style={'fontSize': '13px', 'color': TEXT_LIGHT},
                        ),
                        dbc.Button([
                            "Proceed to Dashboard  →"
                        ], id='btn-confirm-upload', size='lg', style={
                            'backgroundColor': NAVY, 'borderColor': NAVY, 'color': '#FFFFFF',
                            'fontWeight': '700', 'letterSpacing': '0.04em', 'padding': '10px 28px',
                            'fontSize': '14px',
                        }),
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
                ], style={
                    'padding': '16px 24px', 'backgroundColor': '#F1F5F9',
                    'borderTop': f'2px solid {GOLD}', 'borderRadius': '0 0 8px 8px',
                }),
            ], style={
                'border': f'1px solid {BORDER}', 'borderRadius': '8px',
                'boxShadow': '0 4px 20px rgba(0,0,0,0.08)', 'marginTop': '20px',
                'overflow': 'hidden',
            })

            return html.Div(), [analysis_panel]

        except Exception as e:
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"Error: {str(e)}", color="danger"), []

    @app.callback(
        Output('url', 'pathname'),
        Input('btn-confirm-upload', 'n_clicks'),
        prevent_initial_call=True
    )
    def confirm_upload(n_clicks):
        """Redirect to data-review — data was already saved to cache during upload parsing."""
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        return '/data-review'

    # ═══════════════════════════════════════════════════════════════
    # DRILL-THROUGH CALLBACKS (Click on chart to see data)
    # ═══════════════════════════════════════════════════════════════

    @app.callback(
        [Output('drillthrough-modal', 'is_open'),
         Output('store-drillthrough-data', 'data'),
         Output('drillthrough-title', 'children')],
        [Input({'type': 'chart-graph', 'index': ALL}, 'clickData')],
        prevent_initial_call=True
    )
    def open_drillthrough_modal(click_data_list):
        """Open modal when chart is clicked, showing filtered rows for clicked value"""
        if not click_data_list or all(cd is None for cd in click_data_list):
            return False, None, "Record Details"

        clicked = next((cd for cd in click_data_list if cd is not None), None)
        if not clicked:
            return False, None, "Record Details"

        try:
            if not get_cached_df:
                return False, None, "Record Details"

            df = get_cached_df()
            if df is None:
                return False, None, "Record Details"

            point = clicked.get('points', [{}])[0]
            x_val = point.get('x')
            label = point.get('label')
            clicked_val = label if label is not None else x_val

            # Filter rows matching clicked value
            filtered = df
            matched_col = None
            if clicked_val is not None:
                for col in df.select_dtypes(include='object').columns:
                    mask = df[col].astype(str) == str(clicked_val)
                    if mask.sum() > 0:
                        filtered = df[mask]
                        matched_col = col
                        break

            filtered = filtered.head(500).copy()
            for col in filtered.columns:
                try:
                    filtered[col] = filtered[col].astype(str).replace('nan', '').replace('<NA>', '')
                except Exception:
                    pass

            title = f"{clicked_val}" if clicked_val else "Record Details"
            print(f"[DRILL] Clicked '{clicked_val}' in col '{matched_col}', showing {len(filtered)} rows")
            data_json = filtered.to_json(orient='split', default_handler=str)
            return True, data_json, title

        except Exception as e:
            import traceback
            print(f"[WARN] Drill-through error: {e}\n{traceback.format_exc()}")
            return False, None, "Record Details"

    @app.callback(
        [Output('drillthrough-table-container', 'children'),
         Output('drillthrough-badge', 'children'),
         Output('pagination-info', 'children'),
         Output('btn-prev-page', 'disabled'),
         Output('btn-next-page', 'disabled')],
        [Input('store-drillthrough-data', 'data'),
         Input('store-current-page', 'data')],
        prevent_initial_call=True
    )
    def update_drillthrough_table(data_json, current_page):
        """Display themed data table with pagination"""
        empty = html.Div("No data available", style={'color': TEXT_LIGHT, 'padding': '20px', 'textAlign': 'center'})
        if not data_json:
            return empty, "", "", True, True

        try:
            import io
            df = pd.read_json(io.StringIO(data_json), orient='split')
            df = df.astype(str).replace('nan', '').replace('<NA>', '')

            if current_page is None:
                current_page = 0

            rows_per_page = 15
            total_rows = len(df)
            total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
            start_idx = current_page * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)
            page_df = df.iloc[start_idx:end_idx]

            # Navy-themed table header
            TH_STYLE = {
                'fontSize': '10px', 'fontWeight': '700', 'textTransform': 'uppercase',
                'letterSpacing': '0.06em', 'whiteSpace': 'nowrap',
                'backgroundColor': NAVY, 'color': '#FFFFFF',
                'padding': '8px 10px', 'borderBottom': f'2px solid {GOLD}',
            }
            TD_STYLE = {
                'fontSize': '11px', 'whiteSpace': 'nowrap', 'padding': '6px 10px',
                'color': TEXT, 'borderBottom': f'1px solid {BORDER}',
            }
            header = html.Thead(html.Tr([html.Th(c, style=TH_STYLE) for c in page_df.columns]))
            body_rows = []
            for i, row in enumerate(page_df.values):
                row_style = {'backgroundColor': '#F8FAFF' if i % 2 == 0 else '#FFFFFF'}
                body_rows.append(html.Tr(
                    [html.Td(str(v), style={**TD_STYLE}) for v in row],
                    style=row_style
                ))
            table = html.Table(
                [header, html.Tbody(body_rows)],
                style={'width': '100%', 'borderCollapse': 'collapse',
                       'border': f'1px solid {BORDER}', 'borderRadius': '6px'}
            )

            badge = html.Div([
                html.Span(f"{total_rows:,} matching records", style={
                    'fontSize': '12px', 'fontWeight': '600', 'color': NAVY,
                    'backgroundColor': '#EBF4FF', 'padding': '4px 10px',
                    'borderRadius': '12px', 'border': f'1px solid #BFDBFE',
                }),
                html.Span(f"  ·  Showing columns {len(df.columns)}", style={
                    'fontSize': '11px', 'color': TEXT_LIGHT, 'marginLeft': '10px'
                }),
            ])

            info_text = f"Page {current_page + 1} of {total_pages}"
            return table, badge, info_text, current_page == 0, current_page >= total_pages - 1

        except Exception as e:
            import traceback
            print(f"[ERROR] Drillthrough table: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            return html.Div(f"Error: {str(e)[:120]}", style={'color': '#DC2626', 'fontSize': '12px'}), "", "", True, True

    @app.callback(
        Output('store-current-page', 'data'),
        [Input('store-drillthrough-data', 'data'),
         Input('btn-prev-page', 'n_clicks'),
         Input('btn-next-page', 'n_clicks')],
        State('store-current-page', 'data'),
        prevent_initial_call=True
    )
    def update_pagination(drillthrough_data, prev_clicks, next_clicks, current_page):
        """Handle pagination: reset to page 0 when new data loads, or navigate when buttons clicked"""
        ctx = dash.callback_context

        if not ctx.triggered:
            return 0

        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Reset to page 0 when new drillthrough data arrives
        if triggered_id == 'store-drillthrough-data':
            return 0

        # Handle pagination buttons
        if current_page is None:
            current_page = 0

        if triggered_id == 'btn-prev-page':
            return max(0, current_page - 1)
        elif triggered_id == 'btn-next-page':
            return current_page + 1

        return current_page
