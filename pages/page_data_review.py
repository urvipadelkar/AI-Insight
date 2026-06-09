"""Page 1: Data Review - Confirm/correct data types before configuration"""
import pandas as pd
from dash import html, dcc, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
from core.config import PRIMARY_BG, CARD_BG, TEXT, TEXT_LIGHT, BORDER, PRIMARY, SUCCESS
from core.data_profiler import DataProfiler
from core.session_state import SessionState

def generate_data_review_page(df: pd.DataFrame, profiles: dict) -> html.Div:
    """
    Generate the data review page layout
    Shows all columns with detected types and allows user to override types
    """

    # Build table rows
    table_rows = []

    for col_name, profile in sorted(profiles.items()):
        # Handle both object and dict formats
        if isinstance(profile, dict):
            # Profile is a dictionary (from dcc.Store)
            top_values = profile.get('top_values', [])
            dtype = profile.get('dtype', 'categorical')
            cardinality = profile.get('cardinality', 0)
            missing_pct = profile.get('missing_pct', 0)
        else:
            # Profile is an object
            top_values = profile.top_values
            dtype = profile.dtype
            cardinality = profile.cardinality
            missing_pct = profile.missing_pct

        # Get sample value
        sample_val = str(top_values[0]) if top_values else "N/A"

        # Format cardinality and missing info
        cardinality_text = f"{cardinality:,}" if cardinality else "0"
        missing_text = f"{missing_pct:.1f}%"

        # Create type selector dropdown
        type_selector = dcc.Dropdown(
            id={'type': 'dtype-selector', 'index': col_name},
            options=[
                {'label': 'numeric', 'value': 'numeric'},
                {'label': 'categorical', 'value': 'categorical'},
                {'label': 'temporal', 'value': 'temporal'},
                {'label': 'ignore', 'value': 'ignore'},
            ],
            value=dtype,
            clearable=False,
            style={
                'width': '100%',
                'fontSize': '14px',
            }
        )

        # Create table row
        row = html.Tr([
            html.Td(col_name, style={'fontWeight': 'bold', 'padding': '12px'}),
            html.Td(dtype, style={'padding': '12px', 'color': TEXT_LIGHT}),
            html.Td(sample_val, style={'padding': '12px', 'fontSize': '12px', 'color': TEXT_LIGHT}),
            html.Td(cardinality_text, style={'padding': '12px', 'textAlign': 'right', 'color': TEXT_LIGHT}),
            html.Td(missing_text, style={'padding': '12px', 'textAlign': 'right', 'color': TEXT_LIGHT}),
            html.Td(type_selector, style={'padding': '12px', 'width': '150px'}),
        ])

        table_rows.append(row)

    # Count numeric columns (handle both dict and object formats)
    numeric_count = 0
    for prof in profiles.values():
        prof_dtype = prof.get('dtype') if isinstance(prof, dict) else prof.dtype
        if prof_dtype == 'numeric':
            numeric_count += 1

    # Create main layout
    layout = html.Div([
        # Header
        html.Div([
            html.H1("Data Review", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': TEXT}),
            html.P(
                "Review detected data types and make corrections before configuring your dashboard. "
                "Select the appropriate type for each column.",
                style={'color': TEXT_LIGHT, 'marginBottom': '20px'}
            ),
        ], style={'marginBottom': '30px'}),

        # Data Statistics Summary
        html.Div([
            html.Div([
                html.Div([
                    html.Div(f"{len(df):,}", style={'fontSize': '24px', 'fontWeight': 'bold', 'color': PRIMARY}),
                    html.Div("Records", style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginTop': '5px'}),
                ], style={'padding': '15px', 'flex': '1'}),
                html.Div([
                    html.Div(f"{len(profiles)}", style={'fontSize': '24px', 'fontWeight': 'bold', 'color': PRIMARY}),
                    html.Div("Columns", style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginTop': '5px'}),
                ], style={'padding': '15px', 'flex': '1', 'borderLeft': f'1px solid {BORDER}'}),
                html.Div([
                    html.Div(f"{numeric_count}",
                             style={'fontSize': '24px', 'fontWeight': 'bold', 'color': SUCCESS}),
                    html.Div("Numeric", style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginTop': '5px'}),
                ], style={'padding': '15px', 'flex': '1', 'borderLeft': f'1px solid {BORDER}'}),
            ], style={'display': 'flex', 'background': CARD_BG, 'borderRadius': '8px', 'marginBottom': '30px',
                      'border': f'1px solid {BORDER}'}),
        ]),

        # Data Type Review Table
        html.Div([
            html.Div("Column Type Configuration", style={'fontSize': '16px', 'fontWeight': 'bold',
                                                          'color': TEXT, 'marginBottom': '15px'}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Column Name", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '14px',
                                                   'fontWeight': 'bold', 'borderBottom': f'2px solid {PRIMARY}'}),
                    html.Th("Detected Type", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '14px',
                                                    'fontWeight': 'bold', 'borderBottom': f'2px solid {PRIMARY}'}),
                    html.Th("Sample Value", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '14px',
                                                   'fontWeight': 'bold', 'borderBottom': f'2px solid {PRIMARY}'}),
                    html.Th("Cardinality", style={'padding': '12px', 'textAlign': 'right', 'fontSize': '14px',
                                                  'fontWeight': 'bold', 'borderBottom': f'2px solid {PRIMARY}'}),
                    html.Th("Missing %", style={'padding': '12px', 'textAlign': 'right', 'fontSize': '14px',
                                                'fontWeight': 'bold', 'borderBottom': f'2px solid {PRIMARY}'}),
                    html.Th("Confirmed Type", style={'padding': '12px', 'textAlign': 'center', 'fontSize': '14px',
                                                     'fontWeight': 'bold', 'borderBottom': f'2px solid {PRIMARY}'}),
                ])),
                html.Tbody(table_rows),
            ], style={'width': '100%', 'borderCollapse': 'collapse'}),
        ], style={'background': CARD_BG, 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '30px',
                  'border': f'1px solid {BORDER}'}),

        # Navigation Buttons
        html.Div([
            dcc.Link(
                dbc.Button("← Back", outline=True, color="secondary",
                           style={'padding': '10px 20px', 'fontSize': '14px'}),
                href='/',
                style={'textDecoration': 'none'}
            ),
            dcc.Link(
                dbc.Button("Confirm & Continue →", color="primary",
                           style={'padding': '10px 20px', 'fontSize': '14px'}),
                href='/config',
                style={'textDecoration': 'none'}
            ),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '30px'}),

    ], style={'padding': '30px', 'maxWidth': '1200px', 'margin': '0 auto', 'background': PRIMARY_BG, 'minHeight': '100vh'})

    return layout
