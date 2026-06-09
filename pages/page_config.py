"""Page 2: Configuration - User selects KPIs, filters, and aggregations"""
import pandas as pd
from dash import html, dcc, Input, Output, State, callback, ALL
import dash
import dash_bootstrap_components as dbc
from core.config import PRIMARY_BG, CARD_BG, TEXT, TEXT_LIGHT, BORDER, PRIMARY, SUCCESS, WARNING
from core.session_state import KPISelection, FilterSelection
import uuid

def generate_config_page(df: pd.DataFrame, profiles: dict, confirmed_dtypes: dict) -> html.Div:
    """
    Generate the configuration page layout
    User selects KPIs, filters, and aggregation types
    """

    # Handle both dict and object formats for confirmed_dtypes
    # If confirmed_dtypes is empty, use profiles
    if not confirmed_dtypes:
        confirmed_dtypes = {}
        for col, profile in profiles.items():
            if isinstance(profile, dict):
                confirmed_dtypes[col] = profile.get('dtype', 'categorical')
            else:
                confirmed_dtypes[col] = profile.dtype

    # Get numeric and categorical columns based on confirmed types
    numeric_cols = [col for col, dtype in confirmed_dtypes.items() if dtype == 'numeric']
    categorical_cols = [col for col, dtype in confirmed_dtypes.items() if dtype == 'categorical']
    temporal_cols = [col for col, dtype in confirmed_dtypes.items() if dtype == 'temporal']

    # Create layout
    layout = html.Div([
        # Header
        html.Div([
            html.H1("Configure Your Dashboard", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': TEXT}),
            html.P(
                "Select KPIs, aggregation types, and filters. You can add multiple of each.",
                style={'color': TEXT_LIGHT, 'marginBottom': '20px'}
            ),
        ], style={'marginBottom': '30px'}),

        # KPI Configuration Section
        html.Div([
            html.H3("KPI Metrics", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': TEXT, 'marginBottom': '15px'}),

            # KPI selection guide
            html.Div(
                f"Select from {len(numeric_cols)} numeric column{'s' if len(numeric_cols) != 1 else ''}",
                style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginBottom': '10px'}
            ),

            # Multi-select for KPI columns
            dcc.Dropdown(
                id='kpi-column-selector',
                options=[{'label': col, 'value': col} for col in numeric_cols],
                multi=True,
                placeholder="Select columns to add as KPIs...",
                style={'width': '100%', 'marginBottom': '20px'}
            ),

            # Container for selected KPIs
            html.Div(id='kpi-items-container', children=[]),

            # Add KPI button (appears after selection)
            dbc.Button("+ Add Selected as KPI", id='btn-add-kpi', outline=True, color="info",
                       size="sm", style={'marginTop': '15px', 'display': 'none'}),

        ], style={'background': CARD_BG, 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '30px',
                  'border': f'1px solid {BORDER}'}),

        # Filter Configuration Section
        html.Div([
            html.H3("Filters", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': TEXT, 'marginBottom': '15px'}),

            # Filter selection guide
            html.Div(
                f"Select from {len(categorical_cols)} categorical column{'s' if len(categorical_cols) != 1 else ''}",
                style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginBottom': '10px'}
            ),

            # Multi-select for Filter columns
            dcc.Dropdown(
                id='filter-column-selector',
                options=[{'label': col, 'value': col} for col in categorical_cols],
                multi=True,
                placeholder="Select columns to add as filters...",
                style={'width': '100%', 'marginBottom': '20px'}
            ),

            # Container for selected Filters
            html.Div(id='filter-items-container', children=[]),

            # Add Filter button (appears after selection)
            dbc.Button("+ Add Selected as Filter", id='btn-add-filter', outline=True, color="info",
                       size="sm", style={'marginTop': '15px', 'display': 'none'}),

        ], style={'background': CARD_BG, 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '30px',
                  'border': f'1px solid {BORDER}'}),

        # LLM Analysis Section
        html.Div([
            html.Div([
                html.H3("AI Suggestions", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': TEXT}),
                dbc.Button("Get AI Suggestions", id='btn-analyze-ai', color="success", size="sm"),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '15px'}),

            html.Div(
                "Get AI-powered recommendations for additional charts and analysis",
                style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginBottom': '15px'}
            ),

            # Objective input
            html.Div([
                html.Div("ANALYSIS OBJECTIVE", style={
                    'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.08em',
                    'color': '#2B6CB0', 'marginBottom': '6px',
                }),
                dcc.Textarea(
                    id='objective-input',
                    placeholder='e.g. Check monthly trend of expense and performance of the posters...',
                    maxLength=500,
                    rows=3,
                    style={
                        'width': '100%', 'padding': '8px 12px', 'fontSize': '13px',
                        'borderRadius': '6px', 'border': f'1px solid {BORDER}',
                        'resize': 'vertical', 'fontFamily': 'inherit',
                        'backgroundColor': '#F8FBFF',
                    }
                ),
                html.Div(
                    "Optional — steers AI chart and KPI recommendations toward your goal (max 500 chars)",
                    style={'fontSize': '11px', 'color': TEXT_LIGHT, 'marginTop': '4px'}
                ),
            ], style={
                'backgroundColor': '#EBF4FF', 'border': '1px solid #90CDF4',
                'borderLeft': '4px solid #2B6CB0', 'borderRadius': '6px',
                'padding': '12px 16px', 'marginBottom': '16px',
            }),

            # AI Analysis Results (no Loading wrapper — avoids double-spinner with page-level loader)
            html.Div(id='ai-analysis-results', children=[], style={'marginTop': '15px'}),

        ], style={'background': CARD_BG, 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '30px',
                  'border': f'1px solid {BORDER}'}),

        # Hidden stores (note: store-kpi-selections and store-filter-selections are defined in main app.layout)
        dcc.Store(id='store-confirmed-dtypes-from-review', data=confirmed_dtypes),

        # Navigation Buttons
        html.Div([
            dcc.Link(
                dbc.Button("← Back to Data Review", outline=True, color="secondary",
                           style={'padding': '10px 20px', 'fontSize': '14px'}),
                href='/',
                style={'textDecoration': 'none'}
            ),
            dcc.Link(
                dbc.Button("Generate Dashboard →", color="primary",
                           style={'padding': '10px 20px', 'fontSize': '14px'}),
                href='/dashboard',
                style={'textDecoration': 'none'}
            ),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '30px'}),

    ], style={'padding': '30px', 'maxWidth': '1200px', 'margin': '0 auto', 'background': PRIMARY_BG, 'minHeight': '100vh'})

    return layout


def create_kpi_item(kpi_id: str, column: str, aggregation: str = 'sum', label: str = None) -> html.Div:
    """Create a KPI configuration card"""
    if label is None:
        label = f"{aggregation.capitalize()} of {column}"

    return html.Div([
        html.Div([
            html.Div([
                html.Div("Column:", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': TEXT_LIGHT}),
                html.Div(column, style={'fontSize': '14px', 'color': TEXT}),
            ], style={'flex': '1'}),

            html.Div([
                html.Div("Aggregation:", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': TEXT_LIGHT}),
                dcc.Dropdown(
                    id={'type': 'kpi-aggregation', 'index': kpi_id},
                    options=[
                        {'label': 'Sum', 'value': 'sum'},
                        {'label': 'Average', 'value': 'mean'},
                        {'label': 'Count', 'value': 'count'},
                        {'label': 'Max', 'value': 'max'},
                        {'label': 'Min', 'value': 'min'},
                    ],
                    value=aggregation,
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], style={'flex': '1', 'marginLeft': '15px'}),

            html.Div([
                html.Div("Label:", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': TEXT_LIGHT}),
                dcc.Input(
                    id={'type': 'kpi-label', 'index': kpi_id},
                    type='text',
                    value=label,
                    placeholder='e.g., Total Revenue',
                    style={'width': '100%', 'padding': '8px', 'borderRadius': '4px',
                           'border': f'1px solid {BORDER}'}
                ),
            ], style={'flex': '1', 'marginLeft': '15px'}),

            dbc.Button("Remove", id={'type': 'kpi-remove', 'index': kpi_id}, outline=True,
                      color="danger", size="sm", style={'marginTop': '18px', 'marginLeft': '15px'}),
        ], style={'display': 'flex', 'gap': '10px', 'alignItems': 'flex-start'}),
    ], style={'background': '#F9FAFB', 'padding': '15px', 'borderRadius': '6px', 'marginBottom': '10px',
              'border': f'1px solid {BORDER}', 'id': f'kpi-{kpi_id}'})


def create_filter_item(filter_id: str, column: str, filter_type: str = 'dropdown', label: str = None) -> html.Div:
    """Create a filter configuration card"""
    if label is None:
        label = column

    return html.Div([
        html.Div([
            html.Div([
                html.Div("Column:", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': TEXT_LIGHT}),
                html.Div(column, style={'fontSize': '14px', 'color': TEXT}),
            ], style={'flex': '1'}),

            html.Div([
                html.Div("Type:", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': TEXT_LIGHT}),
                dcc.Dropdown(
                    id={'type': 'filter-type', 'index': filter_id},
                    options=[
                        {'label': 'Dropdown', 'value': 'dropdown'},
                        {'label': 'Date Range', 'value': 'date_range'},
                        {'label': 'Numeric Range', 'value': 'numeric_range'},
                    ],
                    value=filter_type,
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], style={'flex': '1', 'marginLeft': '15px'}),

            html.Div([
                html.Div("Label:", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': TEXT_LIGHT}),
                dcc.Input(
                    id={'type': 'filter-label', 'index': filter_id},
                    type='text',
                    value=label,
                    placeholder='e.g., Select Status',
                    style={'width': '100%', 'padding': '8px', 'borderRadius': '4px',
                           'border': f'1px solid {BORDER}'}
                ),
            ], style={'flex': '1', 'marginLeft': '15px'}),

            dbc.Button("Remove", id={'type': 'filter-remove', 'index': filter_id}, outline=True,
                      color="danger", size="sm", style={'marginTop': '18px', 'marginLeft': '15px'}),
        ], style={'display': 'flex', 'gap': '10px', 'alignItems': 'flex-start'}),
    ], style={'background': '#F9FAFB', 'padding': '15px', 'borderRadius': '6px', 'marginBottom': '10px',
              'border': f'1px solid {BORDER}', 'id': f'filter-{filter_id}'})


# Callback to handle KPI selection and rendering
@callback(
    [Output('kpi-items-container', 'children'),
     Output('btn-add-kpi', 'style'),
     Output('store-kpi-selections', 'data')],
    [Input('kpi-column-selector', 'value'),
     Input({'type': 'kpi-remove', 'index': ALL}, 'n_clicks'),
     Input({'type': 'kpi-aggregation', 'index': ALL}, 'value'),
     Input({'type': 'kpi-label', 'index': ALL}, 'value')],
    [State('store-kpi-selections', 'data')],
    allow_duplicate=True
)
def update_kpi_items(selected_columns, remove_clicks, agg_values, label_values, stored_kpis):
    """Update KPI items when columns are selected or aggregations/labels change"""
    if not selected_columns:
        selected_columns = []

    # Create cards for each selected column
    kpi_items = []
    kpi_list = []

    for i, col in enumerate(selected_columns):
        kpi_id = col.replace(' ', '_')

        # Get aggregation and label from inputs if available, otherwise use defaults
        agg = agg_values[i] if agg_values and i < len(agg_values) else 'sum'
        label = label_values[i] if label_values and i < len(label_values) else f"Sum of {col}"

        kpi_item = create_kpi_item(kpi_id, col, agg, label)
        kpi_items.append(kpi_item)
        kpi_list.append({'column': col, 'aggregation': agg, 'label': label})

    # Hide button if no selections
    btn_style = {'marginTop': '15px', 'display': 'block' if selected_columns else 'none'}

    return kpi_items, btn_style, kpi_list


# Callback to handle Filter selection and rendering
@callback(
    [Output('filter-items-container', 'children'),
     Output('btn-add-filter', 'style'),
     Output('store-filter-selections', 'data')],
    [Input('filter-column-selector', 'value'),
     Input({'type': 'filter-remove', 'index': ALL}, 'n_clicks'),
     Input({'type': 'filter-type', 'index': ALL}, 'value'),
     Input({'type': 'filter-label', 'index': ALL}, 'value')],
    [State('store-filter-selections', 'data')],
    allow_duplicate=True
)
def update_filter_items(selected_columns, remove_clicks, type_values, label_values, stored_filters):
    """Update filter items when columns are selected or filter types/labels change"""
    if not selected_columns:
        selected_columns = []

    # Create cards for each selected column
    filter_items = []
    filter_list = []

    for i, col in enumerate(selected_columns):
        filter_id = col.replace(' ', '_')

        # Get filter type and label from inputs if available, otherwise use defaults
        f_type = type_values[i] if type_values and i < len(type_values) else 'dropdown'
        label = label_values[i] if label_values and i < len(label_values) else col

        filter_item = create_filter_item(filter_id, col, f_type, label)
        filter_items.append(filter_item)
        filter_list.append({'column': col, 'filter_type': f_type, 'label': label})

    # Hide button if no selections
    btn_style = {'marginTop': '15px', 'display': 'block' if selected_columns else 'none'}

    return filter_items, btn_style, filter_list


@callback(
    Output('store-objective', 'data'),
    Input('objective-input', 'value'),
    prevent_initial_call=True
)
def sync_objective(value):
    return (value or '').strip()
