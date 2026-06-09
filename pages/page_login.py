"""
Login and Signup Page
Handles user authentication UI
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback
import dash
from core.config import NAVY, GOLD, PRIMARY_BG, CARD_BG, TEXT, TEXT_LIGHT, BORDER, PRIMARY


def generate_login_page():
    """Generate login page layout"""
    
    return dbc.Container([
        dcc.Location(id='url-login', refresh=False),
        
        dbc.Row([
            dbc.Col([
                # Left Side - Branding
                html.Div([
                    html.Div([
                        html.Div("◆", style={'fontSize': '48px', 'color': GOLD, 'marginBottom': '10px'}),
                        html.H1("ONEX AI", style={'color': '#FFFFFF', 'fontWeight': '700', 'marginBottom': '4px'}),
                        html.P("Data Insight", style={'color': GOLD, 'fontSize': '14px', 'fontWeight': '600', 'margin': '0'}),
                    ], style={'textAlign': 'center', 'marginBottom': '40px'}),
                    
                    html.Div([
                        html.H3("AI-Powered Dashboard", style={'color': '#FFFFFF', 'fontWeight': '700', 'marginBottom': '20px'}),
                        html.Ul([
                            html.Li("Auto-detect data patterns", style={'color': TEXT_LIGHT, 'marginBottom': '12px', 'fontSize': '14px'}),
                            html.Li("Generate insightful dashboards", style={'color': TEXT_LIGHT, 'marginBottom': '12px', 'fontSize': '14px'}),
                            html.Li("Connect multiple data sources", style={'color': TEXT_LIGHT, 'marginBottom': '12px', 'fontSize': '14px'}),
                            html.Li("AI-powered recommendations", style={'color': TEXT_LIGHT, 'marginBottom': '12px', 'fontSize': '14px'}),
                        ], style={'paddingLeft': '20px', 'listStyleType': 'none'}),
                    ]),
                ], style={
                    'backgroundColor': NAVY,
                    'padding': '60px 40px',
                    'minHeight': '100vh',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'justifyContent': 'center',
                    'color': '#FFFFFF',
                }),
            ], xs=12, md=6, style={'padding': '0'}),
            
            # Right Side - Login Form
            dbc.Col([
                html.Div([
                    # Tab Selection
                    dbc.Row([
                        dbc.Col([
                            html.Button(
                                "Sign In",
                                id='btn-login-tab',
                                n_clicks=1,
                                style={
                                    'background': 'none',
                                    'border': 'none',
                                    'fontSize': '18px',
                                    'fontWeight': '700',
                                    'color': NAVY,
                                    'cursor': 'pointer',
                                    'paddingBottom': '10px',
                                    'borderBottom': f'3px solid {NAVY}',
                                }
                            ),
                        ], width=6),
                        dbc.Col([
                            html.Button(
                                "Sign Up",
                                id='btn-signup-tab',
                                n_clicks=0,
                                style={
                                    'background': 'none',
                                    'border': 'none',
                                    'fontSize': '18px',
                                    'fontWeight': '700',
                                    'color': TEXT_LIGHT,
                                    'cursor': 'pointer',
                                    'paddingBottom': '10px',
                                }
                            ),
                        ], width=6),
                    ], style={'borderBottom': f'2px solid {BORDER}', 'marginBottom': '40px'}),
                    
                    # Login Form (hidden/shown via callback)
                    html.Div(id='login-form-container', style={'display': 'none'}),
                    
                    # Signup Form (hidden/shown via callback)
                    html.Div(id='signup-form-container', style={'display': 'none'}),
                    
                    # Error Alert
                    html.Div(id='auth-error-message', style={'marginTop': '20px'}),
                    
                ], style={
                    'padding': '60px 40px',
                    'minHeight': '100vh',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'justifyContent': 'center',
                }),
            ], xs=12, md=6, style={'padding': '0', 'backgroundColor': PRIMARY_BG}),
        ], style={'margin': '0', 'height': '100vh'}),
        
    ], fluid=True, style={'padding': '0'})


def get_login_form():
    """Return login form HTML"""
    return html.Div([
        # Username
        html.Div([
            html.Label("Username", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='login-username',
                type='text',
                placeholder='Enter your username',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '20px'}),
        
        # Password
        html.Div([
            html.Label("Password", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='login-password',
                type='password',
                placeholder='Enter your password',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '30px'}),
        
        # Sign In Button
        dbc.Button(
            "Sign In",
            id='btn-sign-in',
            size='lg',
            style={
                'width': '100%',
                'backgroundColor': NAVY,
                'borderColor': NAVY,
                'color': '#FFFFFF',
                'fontWeight': '700',
                'fontSize': '14px',
                'padding': '12px',
            }
        ),
        
        # Forgot Password Link
        html.Div([
            html.A("Forgot password?", href="#", style={'fontSize': '12px', 'color': PRIMARY, 'textDecoration': 'none', 'marginTop': '15px', 'display': 'block'}),
        ]),
    ])


def get_signup_form():
    """Return signup form HTML"""
    return html.Div([
        # First Name
        html.Div([
            html.Label("First Name", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-firstname',
                type='text',
                placeholder='John',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '15px'}),
        
        # Last Name
        html.Div([
            html.Label("Last Name", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-lastname',
                type='text',
                placeholder='Doe',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '15px'}),
        
        # Email
        html.Div([
            html.Label("Email Address", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-email',
                type='email',
                placeholder='john@example.com',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '15px'}),
        
        # Organization
        html.Div([
            html.Label("Organization (Optional)", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-organization',
                type='text',
                placeholder='Acme Corp',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '15px'}),
        
        # Department (Optional)
        html.Div([
            html.Label("Department (Optional)", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Dropdown(
                id='signup-department',
                options=[
                    {'label': 'Finance', 'value': 'Finance'},
                    {'label': 'Operations', 'value': 'Operations'},
                    {'label': 'Sales', 'value': 'Sales'},
                    {'label': 'Marketing', 'value': 'Marketing'},
                    {'label': 'IT', 'value': 'IT'},
                    {'label': 'HR', 'value': 'HR'},
                    {'label': 'Other', 'value': 'Other'},
                ],
                placeholder='Select department',
                style={'fontSize': '14px'}
            ),
        ], style={'marginBottom': '15px'}),
        
        # Username
        html.Div([
            html.Label("Username", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-username',
                type='text',
                placeholder='Choose a username (5-80 chars)',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '15px'}),
        
        # Password
        html.Div([
            html.Label("Password", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-password',
                type='password',
                placeholder='Min 8 chars: uppercase, lowercase, numbers',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '15px'}),
        
        # Confirm Password
        html.Div([
            html.Label("Confirm Password", style={'fontSize': '12px', 'fontWeight': '600', 'color': TEXT, 'display': 'block', 'marginBottom': '6px'}),
            dcc.Input(
                id='signup-password-confirm',
                type='password',
                placeholder='Confirm your password',
                style={
                    'width': '100%',
                    'padding': '12px 14px',
                    'borderRadius': '6px',
                    'border': f'1px solid {BORDER}',
                    'fontSize': '14px',
                    'boxSizing': 'border-box',
                }
            ),
        ], style={'marginBottom': '25px'}),
        
        # Terms checkbox
        html.Div([
            dcc.Checklist(
                id='signup-terms',
                options=[{'label': ' I agree to Terms of Service', 'value': 'agreed'}],
                style={'fontSize': '12px', 'color': TEXT_LIGHT}
            ),
        ], style={'marginBottom': '25px'}),
        
        # Sign Up Button
        dbc.Button(
            "Create Account",
            id='btn-sign-up',
            size='lg',
            style={
                'width': '100%',
                'backgroundColor': NAVY,
                'borderColor': NAVY,
                'color': '#FFFFFF',
                'fontWeight': '700',
                'fontSize': '14px',
                'padding': '12px',
            }
        ),
    ])


# ═════════════════════════════════════════════════════════════════════════
# CALLBACKS FOR TAB SWITCHING
# ═════════════════════════════════════════════════════════════════════════

@callback(
    [Output('login-form-container', 'children'),
     Output('signup-form-container', 'children'),
     Output('btn-login-tab', 'style'),
     Output('btn-signup-tab', 'style')],
    [Input('btn-login-tab', 'n_clicks'),
     Input('btn-signup-tab', 'n_clicks')],
    prevent_initial_call=False
)
def switch_auth_tabs(login_clicks, signup_clicks):
    """Switch between login and signup forms"""
    
    # Determine which tab should be active
    login_active = (login_clicks or 0) >= (signup_clicks or 0)
    
    login_style = {
        'background': 'none',
        'border': 'none',
        'fontSize': '18px',
        'fontWeight': '700',
        'color': NAVY if login_active else TEXT_LIGHT,
        'cursor': 'pointer',
        'paddingBottom': '10px',
        'borderBottom': f'3px solid {NAVY}' if login_active else 'none',
        'transition': 'all 0.3s ease',
    }
    
    signup_style = {
        'background': 'none',
        'border': 'none',
        'fontSize': '18px',
        'fontWeight': '700',
        'color': NAVY if not login_active else TEXT_LIGHT,
        'cursor': 'pointer',
        'paddingBottom': '10px',
        'borderBottom': f'3px solid {NAVY}' if not login_active else 'none',
        'transition': 'all 0.3s ease',
    }
    
    login_form = get_login_form() if login_active else None
    signup_form = get_signup_form() if not login_active else None
    
    return login_form, signup_form, login_style, signup_style
