"""
Upload Page - File upload and data preview (with Database Connection tab)
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
from core.config import PRIMARY_BG, CARD_BG, TEXT, TEXT_LIGHT, BORDER, PRIMARY, SPACING_LG, SPACING_MD, TEXT_MUTED, NAVY, GOLD


def generate_upload_page():
    """Generate file upload page — two source tabs: File Upload and Database"""

    TAB_STYLE = {
        'padding': '10px 24px', 'fontSize': '13px', 'fontWeight': '600',
        'borderRadius': '6px 6px 0 0', 'cursor': 'pointer',
    }
    ACTIVE_TAB_STYLE = {**TAB_STYLE, 'backgroundColor': NAVY, 'color': '#FFFFFF',
                        'borderBottom': f'3px solid {GOLD}'}

    file_tab = dbc.Tab(label="📂 File Upload", tab_id="tab-file", label_style=TAB_STYLE,
                       active_label_style=ACTIVE_TAB_STYLE, children=[
        html.Div([
            html.P(
                "Upload a CSV or Excel file to analyse with AI-powered dashboard generation. "
                "Data will be automatically profiled and visualised.",
                style={'fontSize': '14px', 'color': TEXT_LIGHT, 'marginBottom': '20px'}
            ),
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    html.Div("Drag and drop or ", style={'display': 'inline'}),
                    html.A("select a file", style={'fontWeight': 'bold', 'color': PRIMARY}),
                    html.Div("CSV, XLS, XLSX — max 50 MB",
                             style={'fontSize': '12px', 'color': '#9CA3AF', 'marginTop': '4px'})
                ]),
                style={
                    'width': '100%', 'height': '160px', 'lineHeight': '60px',
                    'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                    'textAlign': 'center', 'cursor': 'pointer',
                    'backgroundColor': PRIMARY_BG, 'borderColor': PRIMARY,
                },
                multiple=False
            ),
            html.Div(
                id='upload-status',
                style={'marginTop': '12px', 'fontSize': '14px'},
                children=html.Div("Maximum file size: 50 MB",
                                  style={'color': '#9CA3AF', 'fontSize': '12px'})
            ),
        ], style={'padding': '24px'}),
    ])

    db_tab = dbc.Tab(label="🗄️ Database", tab_id="tab-db", label_style=TAB_STYLE,
                     active_label_style=ACTIVE_TAB_STYLE, children=[
        html.Div([
            html.P(
                "Connect directly to a database and fetch a table or view into the dashboard.",
                style={'fontSize': '14px', 'color': TEXT_LIGHT, 'marginBottom': '20px'}
            ),

            # Connection form
            html.Div([
                html.Div("CONNECTION SETTINGS", style={
                    'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                    'color': TEXT_LIGHT, 'marginBottom': '12px',
                }),
                html.Div([
                    # DB type
                    html.Div([
                        html.Label("Database Type", style={'fontSize': '12px', 'fontWeight': '600',
                                                            'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Dropdown(
                            id='db-type-dropdown',
                            options=[
                                {'label': 'PostgreSQL', 'value': 'postgresql'},
                                {'label': 'MySQL', 'value': 'mysql'},
                                {'label': 'SQL Server (MSSQL)', 'value': 'mssql'},
                                {'label': 'SQLite (file path)', 'value': 'sqlite'},
                                {'label': 'Oracle', 'value': 'oracle'},
                            ],
                            value='postgresql',
                            clearable=False,
                            style={'fontSize': '13px'}
                        ),
                    ], style={'flex': '1', 'minWidth': '160px'}),

                    # Host
                    html.Div([
                        html.Label("Host / File Path", style={'fontSize': '12px', 'fontWeight': '600',
                                                               'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Input(id='db-host', type='text', placeholder='localhost',
                                  style={'width': '100%', 'padding': '8px 10px', 'borderRadius': '4px',
                                         'border': f'1px solid {BORDER}', 'fontSize': '13px'}),
                    ], style={'flex': '2', 'minWidth': '160px'}),

                    # Port
                    html.Div([
                        html.Label("Port", style={'fontSize': '12px', 'fontWeight': '600',
                                                  'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Input(id='db-port', type='number', placeholder='5432',
                                  style={'width': '100%', 'padding': '8px 10px', 'borderRadius': '4px',
                                         'border': f'1px solid {BORDER}', 'fontSize': '13px'}),
                    ], style={'flex': '1', 'minWidth': '80px'}),

                    # Database name
                    html.Div([
                        html.Label("Database Name", style={'fontSize': '12px', 'fontWeight': '600',
                                                            'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Input(id='db-name', type='text', placeholder='mydb',
                                  style={'width': '100%', 'padding': '8px 10px', 'borderRadius': '4px',
                                         'border': f'1px solid {BORDER}', 'fontSize': '13px'}),
                    ], style={'flex': '2', 'minWidth': '120px'}),
                ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '12px'}),

                html.Div([
                    # Username
                    html.Div([
                        html.Label("Username", style={'fontSize': '12px', 'fontWeight': '600',
                                                      'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Input(id='db-username', type='text', placeholder='postgres',
                                  style={'width': '100%', 'padding': '8px 10px', 'borderRadius': '4px',
                                         'border': f'1px solid {BORDER}', 'fontSize': '13px'}),
                    ], style={'flex': '1', 'minWidth': '120px'}),

                    # Password
                    html.Div([
                        html.Label("Password", style={'fontSize': '12px', 'fontWeight': '600',
                                                      'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Input(id='db-password', type='password', placeholder='••••••••',
                                  style={'width': '100%', 'padding': '8px 10px', 'borderRadius': '4px',
                                         'border': f'1px solid {BORDER}', 'fontSize': '13px'}),
                    ], style={'flex': '1', 'minWidth': '120px'}),

                    # Test connection button
                    html.Div([
                        html.Label(" ", style={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px'}),
                        dbc.Button("Test Connection", id='btn-test-db', size='sm',
                                   style={'backgroundColor': NAVY, 'borderColor': NAVY,
                                          'color': '#fff', 'fontWeight': '600', 'height': '36px',
                                          'whiteSpace': 'nowrap'}),
                    ], style={'flexShrink': '0'}),
                ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '12px'}),

                html.Div(id='db-connection-status', style={'marginBottom': '12px'}),
            ], style={'backgroundColor': '#F8FAFF', 'padding': '16px', 'borderRadius': '6px',
                      'border': f'1px solid {BORDER}', 'marginBottom': '20px'}),

            # Table selector + WHERE builder (shown after connection)
            html.Div(id='db-table-section', children=[
                html.Div([
                    # Table picker
                    html.Div([
                        html.Label("Table / View", style={'fontSize': '12px', 'fontWeight': '600',
                                                          'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Dropdown(id='db-table-dropdown', options=[], placeholder='Select table…',
                                     style={'fontSize': '13px'}),
                    ], style={'flex': '2', 'minWidth': '200px'}),

                    # Row limit
                    html.Div([
                        html.Label("Row limit", style={'fontSize': '12px', 'fontWeight': '600',
                                                       'color': TEXT, 'display': 'block', 'marginBottom': '4px'}),
                        dcc.Input(id='db-row-limit', type='number', value=100000, min=100, max=1000000,
                                  style={'width': '100%', 'padding': '8px 10px', 'borderRadius': '4px',
                                         'border': f'1px solid {BORDER}', 'fontSize': '13px'}),
                    ], style={'flex': '1', 'minWidth': '100px'}),
                ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '16px'}),

                # WHERE clause builder
                html.Div([
                    html.Div("WHERE CONDITIONS (optional)", style={
                        'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                        'color': TEXT_LIGHT, 'marginBottom': '10px',
                    }),
                    html.Div(id='where-conditions-container', children=[]),
                    dbc.Button("+ Add Condition", id='btn-add-where', size='sm', outline=True,
                               color='secondary', style={'marginTop': '8px', 'fontSize': '12px'}),
                ], style={'backgroundColor': '#F8FAFF', 'padding': '14px', 'borderRadius': '6px',
                          'border': f'1px solid {BORDER}', 'marginBottom': '16px'}),

                dbc.Button("Fetch Data →", id='btn-fetch-db', size='lg',
                           style={'backgroundColor': NAVY, 'borderColor': NAVY,
                                  'color': '#fff', 'fontWeight': '700'}),
                html.Div(id='db-fetch-status', style={'marginTop': '10px'}),
            ], style={'display': 'none'}),  # shown by callback after connection

        ], style={'padding': '24px'}),
    ])

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Data Source", className="mb-1",
                        style={'color': NAVY, 'fontWeight': '700', 'fontSize': '26px'}),
                html.P("Upload a file or connect to a database to begin.",
                       style={'color': TEXT_LIGHT, 'marginBottom': '20px', 'fontSize': '14px'}),

                dbc.Tabs(
                    [file_tab, db_tab],
                    id='upload-source-tabs',
                    active_tab='tab-file',
                    style={'borderBottom': f'2px solid {BORDER}', 'marginBottom': '0'},
                ),

                html.Div([
                    dcc.Store(id='db-engine-store', data=None),  # stores serialised connection params
                    # File upload preview (below tabs — visible for both pathways)
                    html.Div(id='preview-container', style={'marginTop': '20px'}),
                    html.Div(id='confirm-container', style={'marginTop': '20px'}),
                ]),
            ], width=12, lg=10, className="mx-auto")
        ], className="mt-4 mb-5"),
    ], fluid=True, style={'backgroundColor': PRIMARY_BG, 'minHeight': '100vh', 'padding': '20px'})
