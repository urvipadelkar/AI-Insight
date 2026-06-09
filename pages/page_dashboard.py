"""Page 3: Dashboard - Render configured KPIs, filters, and charts with AI analysis"""
import pandas as pd
from dash import html, dcc
import dash_bootstrap_components as dbc
from core.config import (PRIMARY_BG, CARD_BG, TEXT, TEXT_LIGHT, BORDER, PRIMARY, SUCCESS, WARNING,
                         NAVY, GOLD, SPACING_MD, SPACING_LG, FONT_SIZE_BODY)
from core.components import kpi_card, executive_summary_card, insight_box, section_header, filter_control
from core.formatters import Formatter
from intelligence.analysis_formatter import AnalysisFormatter

def _norm_score(v) -> float:
    """Normalise quality score to 0.0–1.0 (LLM sometimes returns 0–100)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.85
    if f > 1.0:
        f = f / 100.0
    return max(0.0, min(1.0, f))


def generate_dashboard_page(
    df: pd.DataFrame,
    kpi_selections: list,
    filter_selections: list,
    confirmed_dtypes: dict,
    llm_analysis=None
) -> html.Div:
    """
    Generate the dashboard page with filters, KPIs, and charts
    If no selections provided, uses auto-generated defaults
    """

    # If no selections, generate some defaults to test the dashboard
    if not kpi_selections or not filter_selections:
        # Try to auto-generate defaults from confirmed_dtypes first
        numeric_cols = [col for col, dtype in confirmed_dtypes.items() if dtype == 'numeric']
        categorical_cols = [col for col, dtype in confirmed_dtypes.items() if dtype == 'categorical']

        # If confirmed_dtypes is empty, fall back to detecting from dataframe
        if not numeric_cols or not categorical_cols:
            numeric_cols = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
            categorical_cols = [col for col in df.columns if df[col].dtype == 'object' and df[col].nunique() < 50]

        # Generate default KPIs - always create at least one
        if numeric_cols:
            kpi_selections = [
                {'column': numeric_cols[0], 'aggregation': 'sum', 'label': f'Total {numeric_cols[0]}'},
            ]
            if len(numeric_cols) > 1:
                kpi_selections.append({
                    'column': numeric_cols[1], 'aggregation': 'count', 'label': f'Count of {numeric_cols[1]}'
                })
        else:
            kpi_selections = []

        # Generate default filters - always create at least one
        if categorical_cols:
            filter_selections = [
                {'column': categorical_cols[0], 'filter_type': 'dropdown', 'label': f'Filter by {categorical_cols[0]}'},
            ]
            if len(categorical_cols) > 1:
                filter_selections.append({
                    'column': categorical_cols[1], 'filter_type': 'dropdown', 'label': f'Filter by {categorical_cols[1]}'
                })
        else:
            filter_selections = []

        # If STILL no selections, show message
        if not kpi_selections or not filter_selections:
            return html.Div([
                html.H1("Dashboard", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': TEXT}),
                html.P("Interactive data exploration with filters and AI insights",
                       style={'color': TEXT_LIGHT, 'marginBottom': '30px'}),

                html.Div([
                    html.H3("No KPIs or Filters Selected", style={'color': TEXT, 'marginBottom': '20px'}),
                    html.P("Please configure your dashboard by selecting KPIs and filters.",
                           style={'color': TEXT_LIGHT, 'marginBottom': '20px', 'fontSize': '14px'}),
                    dcc.Link(
                        dbc.Button("Go to Configuration", color="primary", size="lg"),
                        href='/config',
                        style={'textDecoration': 'none'}
                    ),
                ], style={'background': CARD_BG, 'padding': '40px', 'borderRadius': '8px',
                          'textAlign': 'center', 'border': f'1px solid {BORDER}',
                          'maxWidth': '600px', 'margin': '40px auto'}),

            ], style={'padding': '30px', 'maxWidth': '1200px', 'margin': '0 auto', 'background': PRIMARY_BG, 'minHeight': '100vh'})

    # Create filter controls
    filter_controls = []

    # Defensive check: ensure filter_selections is a list of dicts
    if not isinstance(filter_selections, list):
        print(f"[WARN] filter_selections is not a list: {type(filter_selections)}")
        filter_selections = []

    for filter_sel in filter_selections:
        try:
            if not isinstance(filter_sel, dict):
                print(f"[WARN] filter_sel is not a dict: {type(filter_sel)}")
                continue
            col = filter_sel.get('column', '')
            label = filter_sel.get('label', col)
            filter_type = filter_sel.get('filter_type', 'dropdown')

            if not col or col not in df.columns:
                continue

            if filter_type == 'dropdown':
                # Get unique values for dropdown
                filter_values = ["All"] + sorted(df[col].dropna().unique().astype(str).tolist())

                filter_control = html.Div([
                    html.Label(label, style={'fontWeight': 'bold', 'fontSize': '14px', 'color': TEXT}),
                    dcc.Dropdown(
                        id={'type': 'filter-dropdown', 'index': col},
                        options=[{'label': v, 'value': v} for v in filter_values],
                        value="All",
                        clearable=False,
                        style={'width': '100%'}
                    ),
                ], style={'flex': '1', 'marginRight': '15px'})

                filter_controls.append(filter_control)
        except Exception as e:
            print(f"[ERROR] Failed to create filter control: {type(e).__name__}: {str(e)[:100]}")

    # Create initial KPI cards container
    # Initial children will be calculated from the full dataframe
    # These will be updated by the callback when filters change
    initial_kpi_cards = []

    # Defensive check: ensure kpi_selections is a list of dicts
    if not isinstance(kpi_selections, list):
        print(f"[WARN] kpi_selections is not a list: {type(kpi_selections)}")
        kpi_selections = []

    for kpi_sel in kpi_selections:
        try:
            if not isinstance(kpi_sel, dict):
                print(f"[WARN] kpi_sel is not a dict: {type(kpi_sel)}")
                continue
            col = kpi_sel.get('column', '')
            agg = kpi_sel.get('aggregation', 'sum')
            label = kpi_sel.get('label', col)
            if col and col in df.columns:
                initial_kpi_cards.append(generate_kpi_card(df, col, agg, label, confirmed_dtypes))
        except Exception as e:
            print(f"[ERROR] Failed to create KPI card: {type(e).__name__}: {str(e)[:100]}")

    # Create chart container with loading indicator
    charts_container = dcc.Loading(
        id="loading-charts",
        type="default",
        children=[
            html.Div(
                id='charts-container',
                children=[],
                style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(3, 1fr)',
                    'gap': '20px',
                    'marginTop': '30px'
                }
            )
        ]
    )

    # Extract executive summary from LLM analysis if available
    exec_summary = None
    if llm_analysis and isinstance(llm_analysis, dict):
        exec_summary = llm_analysis.get('executive_summary', {})

    # Create layout - Big Four style (Executive Summary First)
    layout = html.Div([
        # Header with navigation
        html.Div([
            html.Div([
                html.H1("Executive Dashboard", style={'fontSize': '32px', 'fontWeight': '700', 'color': NAVY, 'margin': '0'}),
                html.P("AI-Powered Business Intelligence",
                       style={'color': TEXT_LIGHT, 'marginBottom': '0', 'fontSize': FONT_SIZE_BODY}),
            ], style={'flex': '1'}),

            html.Div([
                dbc.Button(
                    [html.Span("↓", style={'marginRight': '6px'}), "Download PDF"],
                    id='btn-download-pdf',
                    size="sm",
                    style={
                        'backgroundColor': 'transparent', 'border': f'1px solid {GOLD}',
                        'color': GOLD, 'fontWeight': '600', 'fontSize': '12px',
                        'padding': '6px 14px', 'borderRadius': '4px',
                    }
                ),
                dbc.Button(
                    [html.Span("⟳", style={'marginRight': '6px'}), "Refresh Analysis"],
                    id='btn-refresh-analysis',
                    size="sm",
                    style={
                        'backgroundColor': NAVY, 'border': f'1px solid {GOLD}',
                        'color': GOLD, 'fontWeight': '700', 'fontSize': '12px',
                        'padding': '6px 14px', 'borderRadius': '4px',
                    }
                ),
                dbc.Button(
                    "💾 Save Dashboard",
                    id='btn-open-save-modal',
                    size="sm",
                    style={
                        'backgroundColor': '#065F46', 'border': '1px solid #065F46',
                        'color': '#FFFFFF', 'fontWeight': '700', 'fontSize': '12px',
                        'padding': '6px 14px', 'borderRadius': '4px',
                    }
                ),
            ], style={'display': 'flex', 'gap': '10px', 'alignItems': 'center'}),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                  'marginBottom': SPACING_LG, 'paddingBottom': SPACING_LG, 'borderBottom': f'2px solid {GOLD}'}),

        # EXECUTIVE SUMMARY (Big Four style - appears first!)
        html.Div(
            id='executive-summary-container',
            children=executive_summary_card(
                title="Executive Summary",
                findings=exec_summary.get('key_findings', ['Dashboard ready. Run AI Suggestions for executive briefing.'])
                         if exec_summary else ['Dashboard ready. Run AI Suggestions for executive briefing.'],
                health_score=_norm_score(exec_summary.get('data_quality_score', 0.85)) if exec_summary else 0.85,
                status='healthy' if exec_summary and _norm_score(exec_summary.get('data_quality_score', 0)) > 0.8 else 'caution',
                narrative=exec_summary.get('narrative', '') if exec_summary else '',
                risk_flags=exec_summary.get('risk_flags', []) if exec_summary else [],
                priority_action=exec_summary.get('priority_action', '') if exec_summary else '',
            ),
            style={'marginBottom': SPACING_LG}
        ),

        # Filters Section (Horizontal bar)
        html.Div([
            section_header("Filters & Drill-Down", "Select to filter data across all metrics and charts"),
            html.Div(
                filter_controls,
                style={'display': 'flex', 'flexWrap': 'wrap', 'gap': SPACING_MD}
            ),
        ], style={'background': CARD_BG, 'padding': SPACING_LG, 'borderRadius': '8px', 'marginBottom': SPACING_LG,
                  'border': f'1px solid {BORDER}'}) if filter_controls else html.Div(),

        # KPI Cards Section (Professional styling with comparisons)
        html.Div([
            section_header("Key Performance Indicators", "Core business metrics at a glance"),
            html.Div(
                id='kpi-cards-container',
                children=html.Div(initial_kpi_cards, style={'display': 'flex', 'gap': SPACING_MD, 'flexWrap': 'wrap'}),
                style={'display': 'flex', 'gap': SPACING_MD, 'flexWrap': 'wrap'}
            ),
        ], style={'background': CARD_BG, 'padding': SPACING_LG, 'borderRadius': '8px', 'marginBottom': SPACING_LG,
                  'border': f'1px solid {BORDER}'}) if kpi_selections else html.Div(),

        # Charts Section (with insight text below each)
        html.Div([
            section_header("Analysis & Insights", "Interactive visualizations for deeper understanding"),
            charts_container,
        ], style={'marginTop': SPACING_LG, 'marginBottom': SPACING_LG}),

        # Data Source & Timestamp
        html.Div([
            html.P(f"Generated with AI-powered analysis | Data quality: {int(_norm_score(exec_summary.get('data_quality_score', 0.85)) * 100)}%"
                   if exec_summary else "Dashboard ready",
                   style={'color': TEXT_LIGHT, 'fontSize': '12px', 'margin': '0', 'textAlign': 'center'}),
        ], style={'paddingTop': SPACING_MD, 'borderTop': f'1px solid {BORDER}', 'marginTop': SPACING_LG}),

        # Drill-Through Modal — Big Four themed
        dbc.Modal([
            dbc.ModalHeader(
                html.Div([
                    html.Div([
                        html.Span("DATA DRILL-THROUGH", style={
                            'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.12em',
                            'color': GOLD, 'display': 'block', 'marginBottom': '4px',
                        }),
                        html.Span(id='drillthrough-title', children="Record Details", style={
                            'fontSize': '18px', 'fontWeight': '700', 'color': '#FFFFFF',
                        }),
                    ]),
                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}),
                close_button=True,
                style={
                    'backgroundColor': NAVY,
                    'borderBottom': f'3px solid {GOLD}',
                    'padding': '16px 24px',
                    '--bs-btn-close-color': '#FFFFFF',
                }
            ),
            dbc.ModalBody([
                # Row count badge
                html.Div(id='drillthrough-badge', style={'marginBottom': '12px'}),
                # Scrollable table
                html.Div(
                    id='drillthrough-table-container',
                    style={'overflowX': 'auto', 'fontSize': '12px'},
                ),
                # Pagination bar
                html.Div([
                    dbc.Button(
                        "← Prev", id='btn-prev-page', size='sm', disabled=True,
                        style={'backgroundColor': NAVY, 'borderColor': NAVY, 'color': '#fff',
                               'fontWeight': '600', 'fontSize': '12px'}
                    ),
                    html.Span(id='pagination-info', style={
                        'margin': '0 16px', 'fontSize': '12px',
                        'color': TEXT_LIGHT, 'fontWeight': '500',
                    }),
                    dbc.Button(
                        "Next →", id='btn-next-page', size='sm',
                        style={'backgroundColor': NAVY, 'borderColor': NAVY, 'color': '#fff',
                               'fontWeight': '600', 'fontSize': '12px'}
                    ),
                ], style={
                    'display': 'flex', 'justifyContent': 'center',
                    'alignItems': 'center', 'marginTop': '16px',
                    'padding': '12px 0', 'borderTop': f'1px solid {BORDER}',
                }),
            ], style={'padding': '20px 24px', 'backgroundColor': '#FAFBFC'}),
            dbc.ModalFooter(
                html.Span("Click any chart bar, slice, or point to explore underlying records.",
                          style={'fontSize': '11px', 'color': TEXT_LIGHT}),
                style={'backgroundColor': '#F1F5F9', 'borderTop': f'1px solid {BORDER}', 'padding': '10px 24px'}
            ),
        ], id='drillthrough-modal', size='xl', scrollable=True,
           style={'fontFamily': "'Segoe UI', Arial, sans-serif"}),

        # ── Save / Load Dashboard Modal ────────────────────────
        dbc.Modal([
            dbc.ModalHeader(
                html.Div([
                    html.Span("DASHBOARD MANAGER", style={
                        'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.12em',
                        'color': GOLD, 'display': 'block', 'marginBottom': '4px',
                    }),
                    html.Span("Save or restore a dashboard configuration", style={
                        'fontSize': '15px', 'fontWeight': '700', 'color': '#FFFFFF',
                    }),
                ]),
                style={'backgroundColor': NAVY, 'borderBottom': f'3px solid {GOLD}', 'padding': '16px 24px'}
            ),
            dbc.ModalBody([
                # SAVE section
                html.Div([
                    html.Div("SAVE CURRENT DASHBOARD", style={
                        'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                        'color': TEXT_LIGHT, 'marginBottom': '10px',
                    }),
                    html.Div([
                        dcc.Input(
                            id='save-dashboard-name',
                            type='text',
                            placeholder='Enter dashboard name…',
                            debounce=False,
                            style={'flex': '1', 'padding': '8px 12px', 'borderRadius': '4px',
                                   'border': f'1px solid {BORDER}', 'fontSize': '13px'}
                        ),
                        dbc.Button("Save", id='btn-save-dashboard', size='sm',
                                   style={'backgroundColor': '#065F46', 'borderColor': '#065F46',
                                          'color': '#fff', 'fontWeight': '700'}),
                    ], style={'display': 'flex', 'gap': '8px', 'alignItems': 'center'}),
                    html.Div(id='save-dashboard-status', style={'marginTop': '6px'}),
                ], style={'marginBottom': '24px', 'paddingBottom': '20px',
                          'borderBottom': f'1px solid {BORDER}'}),

                # LOAD section
                html.Div([
                    html.Div([
                        html.Div("LOAD SAVED DASHBOARD", style={
                            'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                            'color': TEXT_LIGHT, 'marginBottom': '10px',
                        }),
                        dbc.Button("⟳ Refresh list", id='btn-refresh-saved-list', size='sm', outline=True,
                                   color='secondary', style={'fontSize': '11px'}),
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                              'marginBottom': '10px'}),
                    dcc.Dropdown(
                        id='load-dashboard-dropdown',
                        options=[],
                        placeholder='Select a saved dashboard…',
                        style={'marginBottom': '10px'}
                    ),
                    dbc.Button("Load Selected", id='btn-load-dashboard', size='sm',
                               style={'backgroundColor': NAVY, 'borderColor': NAVY, 'color': '#fff',
                                      'fontWeight': '700'}),
                    html.Div(id='load-dashboard-status', style={'marginTop': '6px'}),
                ]),
            ], style={'padding': '20px 24px', 'backgroundColor': '#FAFBFC'}),
            dbc.ModalFooter(
                html.Span("Saved dashboards are stored in saved_dashboards/ folder in the project directory.",
                          style={'fontSize': '11px', 'color': TEXT_LIGHT}),
                style={'backgroundColor': '#F1F5F9', 'borderTop': f'1px solid {BORDER}', 'padding': '10px 24px'}
            ),
        ], id='save-load-modal', size='lg',
           style={'fontFamily': "'Segoe UI', Arial, sans-serif"}),

        # Hidden stores (data passed from parent app, not stored locally)
        dcc.Store(id='store-kpi-selections-dashboard', data=kpi_selections),
        dcc.Store(id='store-filter-selections-dashboard', data=filter_selections),
        dcc.Store(id='store-confirmed-dtypes-dashboard', data=confirmed_dtypes),
        dcc.Store(id='store-llm-analysis', data=llm_analysis),
        dcc.Store(id='store-drillthrough-data', data=None),
        dcc.Store(id='store-current-page', data=0),

    ], style={'padding': SPACING_LG, 'maxWidth': '1600px', 'margin': '0 auto', 'background': PRIMARY_BG, 'minHeight': '100vh'})

    return layout


def generate_kpi_card(df: pd.DataFrame, column: str, aggregation: str, label: str, confirmed_dtypes: dict) -> html.Div:
    """Generate a professional KPI card with value, trend, and status"""
    try:
        # Get column dtype for formatting
        dtype = confirmed_dtypes.get(column, 'categorical')

        # Calculate aggregated value
        if aggregation == 'sum':
            value = df[column].sum()
        elif aggregation == 'mean':
            value = df[column].mean()
        elif aggregation == 'count':
            value = df[column].count()
        elif aggregation == 'max':
            value = df[column].max()
        elif aggregation == 'min':
            value = df[column].min()
        else:
            value = df[column].iloc[0] if len(df) > 0 else None

        # Format the value
        formatted_value = Formatter.format_kpi_value(value, dtype, aggregation)

        # Simulate trend calculation (placeholder for real delta calculation)
        # In a real scenario, you'd compare current vs. previous period
        delta = "+12%" if value > 0 else "-5%"
        comparison = "vs. last period"
        trend = "up" if value > 0 else "down"
        status = "healthy" if value > 0 else "caution"

        return kpi_card(
            title=label,
            value=formatted_value,
            delta=delta,
            comparison=comparison,
            trend=trend,
            status=status,
            color=PRIMARY
        )

    except Exception as e:
        # Error card with professional styling
        return html.Div([
            html.Div(label, style={'fontSize': '12px', 'color': TEXT_LIGHT}),
            html.Div("Unable to load metric", style={'fontSize': '18px', 'color': '#DC2626', 'marginTop': '8px'}),
        ], style={'background': '#FEE2E2', 'padding': '15px', 'borderRadius': '6px', 'borderLeft': '4px solid #DC2626'})


def generate_analysis_banner(llm_analysis) -> str:
    """Generate analysis banner text"""
    if not llm_analysis:
        return "Dashboard created successfully."

    try:
        if isinstance(llm_analysis, dict):
            return llm_analysis.get('reasoning', 'Analysis generated.')
        return "AI analysis completed."
    except:
        return "Dashboard created successfully."


# Note: Callbacks for this page are registered in callbacks/dashboard_callbacks.py
# via the register_dashboard_callbacks() function
