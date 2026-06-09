"""Build dashboard layouts from column profiles"""
from core.config import FilterConfig, KPIConfig, ChartConfig, DashboardConfig, SUCCESS, WARNING, DANGER
from core.data_profiler import ColumnProfile, get_key_metrics, get_filter_candidates
from intelligence.chart_recommender import ChartRecommender
from typing import Dict, List, Optional

class LayoutBuilder:
    """Generate DashboardConfig from column profiles"""

    def __init__(self):
        self.recommender = ChartRecommender()

    def build_config(self, profiles: Dict[str, ColumnProfile],
                    user_context: str = None) -> DashboardConfig:
        """Generate COMPREHENSIVE DashboardConfig analyzing ALL columns"""

        # 1. Identify filters (low cardinality categorical) - max 3-5
        filter_cols = get_filter_candidates(profiles)[:5]  # Up to 5 filters
        filters = [
            FilterConfig(
                column=col,
                filter_type='dropdown',
                label=col.replace('_', ' ').title()
            )
            for col in filter_cols
        ]

        # 2. Identify metrics (numeric columns) - max 4
        metrics = get_key_metrics(profiles)[:4]  # Up to 4 metrics

        # 3. Generate KPI cards for top metrics
        kpis = []
        if metrics:
            colors = [SUCCESS, WARNING, DANGER, SUCCESS]
            for i, metric in enumerate(metrics[:4]):
                kpis.append(KPIConfig(
                    metric=metric,
                    aggregation='sum' if i == 0 else ('mean' if i == 1 else 'max'),
                    label=f"{'Total' if i == 0 else ('Avg' if i == 1 else 'Max')} {metric}",
                    color=colors[i % len(colors)]
                ))

        # 4. COMPREHENSIVE CHART ANALYSIS - analyze ALL useful columns
        charts = []
        chart_id_counter = 0

        # Separate columns by type
        numeric_cols = [name for name, p in profiles.items()
                       if p.dtype == 'numeric' and not p.is_key_field]
        categorical_cols = [name for name, p in profiles.items()
                           if p.dtype == 'categorical' and not p.is_key_field]
        temporal_cols = [name for name, p in profiles.items() if p.is_temporal]

        # ============= CATEGORICAL ANALYSIS =============
        # Chart 1-5: Distribution for each categorical column (top 5)
        for cat_col in categorical_cols[:5]:
            chart_id_counter += 1
            # Skip ultra-high cardinality (like IDs)
            if profiles[cat_col].cardinality > 100:
                continue

            charts.append(ChartConfig(
                chart_id=f'category-dist-{chart_id_counter}',
                chart_type='bar',
                x_column=cat_col,
                y_column=cat_col,
                size='1/3',
                aggregation='count',
                title=f"Distribution: {cat_col.replace('_', ' ')}"
            ))

        # ============= NUMERIC ANALYSIS =============
        # For each numeric column, create multiple visualizations
        for num_col in numeric_cols[:6]:  # Top 6 numeric columns
            # Chart: Histogram (distribution)
            chart_id_counter += 1
            charts.append(ChartConfig(
                chart_id=f'numeric-hist-{chart_id_counter}',
                chart_type='histogram',
                x_column=num_col,
                y_column=num_col,
                size='1/3',
                aggregation='raw',
                title=f"Distribution: {num_col.replace('_', ' ')}"
            ))

            # Chart: Box plot (quartiles, outliers)
            chart_id_counter += 1
            if len(categorical_cols) > 0:
                charts.append(ChartConfig(
                    chart_id=f'numeric-box-{chart_id_counter}',
                    chart_type='box',
                    x_column=categorical_cols[0],
                    y_column=num_col,
                    size='1/3',
                    aggregation='raw',
                    title=f"{num_col} by {categorical_cols[0]}"
                ))

        # ============= TEMPORAL ANALYSIS =============
        # For each temporal column, create time-series chart
        for temp_col in temporal_cols[:3]:  # Top 3 temporal columns
            if len(metrics) > 0:
                chart_id_counter += 1
                charts.append(ChartConfig(
                    chart_id=f'temporal-trend-{chart_id_counter}',
                    chart_type='line',
                    x_column=temp_col,
                    y_column=metrics[0],  # First metric over time
                    size='1/2',
                    aggregation='sum',
                    title=f"{metrics[0]} Over {temp_col.replace('_', ' ')}"
                ))
            else:
                # If no metrics, just count records by date
                chart_id_counter += 1
                charts.append(ChartConfig(
                    chart_id=f'temporal-count-{chart_id_counter}',
                    chart_type='bar',
                    x_column=temp_col,
                    y_column=temp_col,
                    size='1/2',
                    aggregation='count',
                    title=f"Records by {temp_col.replace('_', ' ')}"
                ))

        # ============= CROSS-TABULATION ANALYSIS =============
        # If we have both categorical and numeric, create aggregate view
        if categorical_cols and numeric_cols:
            chart_id_counter += 1
            charts.append(ChartConfig(
                chart_id=f'crosstab-{chart_id_counter}',
                chart_type='bar',
                x_column=categorical_cols[0],
                y_column=numeric_cols[0],
                size='1/2',
                aggregation='sum',
                title=f"{numeric_cols[0]} by {categorical_cols[0]}"
            ))

        # ============= CORRELATION ANALYSIS =============
        # Add heatmap if we have multiple numeric columns
        if len(numeric_cols) >= 3:
            chart_id_counter += 1
            charts.append(ChartConfig(
                chart_id=f'correlation-heatmap',
                chart_type='heatmap',
                x_column=numeric_cols[0],
                y_column=numeric_cols[1],
                size='full',
                aggregation='raw',
                title="Correlation Matrix: Numeric Columns"
            ))

        # Limit total charts to reasonable number (8-12)
        charts = charts[:12]

        # Layout grid based on chart count
        if len(charts) >= 9:
            layout_grid = '3-col'
        elif len(charts) >= 5:
            layout_grid = '2-col'
        else:
            layout_grid = '1-col'

        print(f"[OK] Generated comprehensive dashboard:")
        print(f"  - Filters: {len(filters)}")
        print(f"  - KPIs: {len(kpis)}")
        print(f"  - Charts: {len(charts)} (analyzing all column types)")
        print(f"  - Layout: {layout_grid}")

        return DashboardConfig(
            filters=filters,
            kpis=kpis,
            charts=charts,
            layout_grid=layout_grid,
            reasoning="Comprehensive auto-generated dashboard analyzing ALL column types (Phase 2 Enhanced)"
        )
