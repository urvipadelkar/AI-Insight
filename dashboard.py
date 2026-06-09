"""
Intelligent Data Dashboard - Multi-Page Architecture (All Phases Integrated)
=============================================================================
Phases:
1. Code Refactoring - Modular architecture
2. Intelligence Layer - Auto-analysis & recommendations
3. LLM Integration - LMStudio + Claude fallback
4. User Interaction - Multi-page flow with user customization

Pages:
1. /data-review - Confirm/correct detected data types
2. /config - Select KPIs, filters, and aggregations
3. /dashboard - Render dashboard with user selections

Usage:
    python dashboard.py
    Open http://0.0.0.0:8050
"""

import os
import json
import pickle
import warnings
import pandas as pd
import numpy as np
import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, callback, ALL
import plotly.express as px
import plotly.graph_objects as go

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════
# IMPORTS - Modular Architecture
# ═══════════════════════════════════════════════════════════════
from core.config import *
from core.components import kpi_card, filter_control, chart_container
from core.data_profiler import DataProfiler, get_filter_candidates, get_key_metrics
from core.formatters import Formatter
from intelligence.layout_builder import LayoutBuilder
from intelligence.insight_extractor import InsightExtractor
from intelligence.llm_analyzer import LLMAnalyzer
from intelligence.analysis_formatter import AnalysisFormatter
from intelligence.chart_analyzer import ChartAnalyzer
from llm.config import LLMFactory, DEFAULT_CONFIG
from llm.prompts import build_big_four_prompt

# Import page modules
from pages import page_data_review, page_config, page_dashboard, page_upload
from callbacks.dashboard_callbacks import register_dashboard_callbacks
from core.dashboard_store import save as save_dashboard, list_saved, load as load_dashboard, delete as delete_dashboard
from core import db_connector
from core import query_builder

# Server-side holder for the active DB engine (not serialisable to dcc.Store)
_current_db = {'engine': None, 'db_type': None}

# ═══════════════════════════════════════════════════════════════
# PHASE 1: DATA LOADING (Original + Enhanced)
# ═══════════════════════════════════════════════════════════════

def load_data(path: str) -> pd.DataFrame:
    """Load data from cache or CSV or generate sample

    Priority:
    1. Check for active user upload
    2. Check for default CSV path
    3. Generate sample data
    """
    from core.cache_manager import CacheManager

    # Check for active user upload first
    active_upload_path = CacheManager.get_active_upload_path()
    if active_upload_path and os.path.exists(active_upload_path):
        print(f"[OK] Loading active user upload: {active_upload_path}")
        try:
            with open(active_upload_path, 'rb') as f:
                df = pickle.load(f)
            print(f"[OK] Loaded {df.shape[0]:,} rows x {df.shape[1]} cols from user upload")
            return df
        except Exception as e:
            print(f"[WARN] Failed to load active upload: {e}, falling back to default")

    # Fall back to default data path
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=True)
        print(f"[OK] Loaded real data from {path} -> {df.shape[0]:,} rows x {df.shape[1]} cols")
        return df

    print("[INFO] CSV not found - using built-in sample data")
    np.random.seed(42)
    n = 500
    categories = ["Electronics", "Clothing", "Food", "Furniture", "Sports"]
    regions = ["North", "South", "East", "West"]
    dates = pd.date_range("2023-01-01", periods=n, freq="D")

    df = pd.DataFrame({
        "date": np.random.choice(dates, n),
        "category": np.random.choice(categories, n),
        "region": np.random.choice(regions, n),
        "sales": np.random.randint(100, 5000, n),
        "profit": np.random.randint(10, 1000, n),
        "units": np.random.randint(1, 50, n),
        "discount": np.round(np.random.uniform(0, 0.4, n), 2),
    })
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# Load data ONCE at startup
df = load_data(DATA_PATH)

# Save to file to avoid dcc.Store serialization issues
cache_dir = os.path.join(os.path.dirname(__file__), '.cache')
os.makedirs(cache_dir, exist_ok=True)
df_pickle_path = os.path.join(cache_dir, 'dataframe.pkl')
profiles_json_path = os.path.join(cache_dir, 'profiles.json')

from pandas.api.types import is_numeric_dtype as _is_num_startup

df_processed = df.copy()
_coerced = 0
for _col in df_processed.columns:
    if not _is_num_startup(df_processed[_col]):
        try:
            _cleaned = (df_processed[_col].astype(str)
                        .str.replace(r'[,\u20B9$\u20AC\xa3]', '', regex=True)
                        .str.strip())
            _converted = pd.to_numeric(_cleaned, errors='coerce')
            if _converted.notna().sum() / max(len(df_processed), 1) > 0.5:
                df_processed[_col] = _converted
                _coerced += 1
        except Exception:
            pass
print(f"[OK] Startup coercion: {_coerced} columns converted to numeric")

# Use pickle to handle mixed data types in columns (parquet is too strict)
with open(df_pickle_path, 'wb') as f:
    pickle.dump(df_processed, f)
print(f"[OK] DataFrame cached to {df_pickle_path}")

# Helper function to load cached dataframe
def get_cached_dataframe():
    """Load dataframe from cache -- user upload takes priority over default data.

    Applies numeric coercion at load time so ALL callers (KPI, charts, drillthrough)
    receive properly-typed data without each needing its own coercion block.
    """
    df = None
    try:
        from core.cache_manager import CacheManager
        active_path = CacheManager.get_active_upload_path()
        if active_path and os.path.exists(active_path):
            with open(active_path, 'rb') as f:
                df = pickle.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load active upload in get_cached_dataframe: {e}")

    if df is None:
        try:
            with open(df_pickle_path, 'rb') as f:
                df = pickle.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load cached dataframe: {e}")
            return None

    return df.copy()

def load_cached_profiles():
    """Load column profiles — active upload takes priority over default data.csv profiles."""
    try:
        from core.cache_manager import CacheManager
        upload_profiles_path = CacheManager.get_active_upload_profiles_path()
        if upload_profiles_path and os.path.exists(upload_profiles_path):
            with open(upload_profiles_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load upload profiles: {e}")

    try:
        with open(profiles_json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not load profiles: {e}")
        return {}

# ═══════════════════════════════════════════════════════════════
# PHASE 2: AUTO-ANALYSIS (Intelligence Layer)
# ═══════════════════════════════════════════════════════════════

print("\n[INFO] Phase 2: Analyzing data structure...")
profiler = DataProfiler()
profiles = profiler.profile(df)

# Print detected columns
print("[OK] Data Analysis:")
for name, profile in profiles.items():
    print(f"  - {name}: {profile.dtype} (cardinality={profile.cardinality}, missing={profile.missing_pct:.1f}%)")

# Cache profiles to JSON file for later use in callbacks
profiles_dict = {
    name: {
        'dtype': profile.dtype,
        'cardinality': profile.cardinality,
        'missing_pct': profile.missing_pct,
        'value_range': profile.value_range if hasattr(profile, 'value_range') else None,
        'top_values': profile.top_values if hasattr(profile, 'top_values') else None,
        'is_temporal': profile.is_temporal,
        'has_outliers': profile.has_outliers if hasattr(profile, 'has_outliers') else False,
    }
    for name, profile in profiles.items()
}
with open(profiles_json_path, 'w') as f:
    json.dump(profiles_dict, f, indent=2, default=str)
print(f"[OK] Profiles cached to {profiles_json_path}")

# Generate auto-layout
print("\n[INFO] Phase 1-2: Generating auto-layout...")
builder = LayoutBuilder()
auto_config = builder.build_config(profiles)
print(f"[OK] Auto-generated {len(auto_config.charts)} charts, {len(auto_config.filters)} filters, {len(auto_config.kpis)} KPIs")

# Extract insights
insight_extractor = InsightExtractor()
insights = insight_extractor.extract(df, profiles)
if insights:
    print("\n[WARN] Data Quality Issues:")
    for insight in insights:
        print(f"  - {insight.description}")

# ═══════════════════════════════════════════════════════════════
# PHASE 3: LLM ANALYSIS (Optional - Ollama/LMStudio/Claude)
# ═══════════════════════════════════════════════════════════════

llm_config = None
llm_config_obj = None
llm_analyzer = None
provider = None
dashboard_config = auto_config

try:
    # Try to load LLM config - check both relative and absolute paths
    config_paths = [
        "llm_config.json",
        os.path.join(os.path.dirname(__file__), "llm_config.json"),
        os.path.join(os.getcwd(), "llm_config.json"),
        r"D:\test\llm_config.json"
    ]

    llm_config_path = None
    for path in config_paths:
        if os.path.exists(path):
            llm_config_path = path
            break

    if llm_config_path:
        with open(llm_config_path) as f:
            llm_config = json.load(f)
        print(f"\n[OK] Found llm_config.json at: {llm_config_path}")
        print(f"[OK] Loaded LLM config: provider={llm_config.get('provider')}")

        # Create LLM provider
        config_obj = DEFAULT_CONFIG
        if llm_config.get('provider'):
            config_obj.provider = llm_config['provider']
        if llm_config.get('model_name'):
            config_obj.model_name = llm_config['model_name']
        if llm_config.get('base_url'):
            config_obj.base_url = llm_config['base_url']
        if llm_config.get('api_key'):
            config_obj.api_key = llm_config['api_key']
        if llm_config.get('include_sample_data') is not None:
            config_obj.include_sample_data = llm_config['include_sample_data']

        llm_config_obj = config_obj

        # Run LLM analysis with timeout and better error handling
        print("\n[INFO] Phase 3: Analyzing with LLM...")
        print(f"[INFO] Using provider: {config_obj.provider} at {config_obj.base_url}")

        try:
            print("[INFO] Creating LLM provider and analyzer...")
            provider = LLMFactory.create(config_obj)
            llm_analyzer = LLMAnalyzer(provider, config_obj)  # IMPORTANT: Initialize analyzer first
            print("[OK] LLM analyzer created successfully")

            user_context = f"Dataset contains {len(df):,} records with {len(profiles)} columns. Primary use case: data exploration and KPI monitoring."

            print(f"[INFO] Running startup LLM analysis (may take 1-5 minutes)...")
            print(f"[INFO] Ollama endpoint: {config_obj.base_url}")

            # Run LLM analysis - but don't fail if it times out
            try:
                llm_config_result = llm_analyzer.analyze(df, profiles, user_context)
                if llm_config_result:
                    dashboard_config = llm_config_result
                    print("[OK] LLM analysis successful, using AI-generated configuration")
                else:
                    dashboard_config = auto_config
                    print("[WARN] LLM returned empty result, using auto-layout")
            except (TimeoutError, ConnectionError) as analysis_error:
                print(f"\n[WARN] LLM analysis timeout (startup only)")
                print(f"[INFO] The 'Get AI Suggestions' button will still work on-demand")
                dashboard_config = auto_config
            except Exception as analysis_error:
                print(f"\n[WARN] LLM analysis failed during startup: {type(analysis_error).__name__}")
                print(f"[INFO] {str(analysis_error)[:150]}")
                print(f"[INFO] The 'Get AI Suggestions' button will still work on-demand")
                dashboard_config = auto_config

        except (TimeoutError, ConnectionError) as e:
            print(f"\n[WARN] LLM initialization failed - Server connection issue")
            print(f"[ERROR] {type(e).__name__}: {str(e)[:150]}")
            print(f"[INFO] Ollama server: {config_obj.base_url}")
            print(f"\n[SOLUTION]")
            print(f"  Option 1: Use local Ollama (Recommended)")
            print(f"    - Update llm_config.json: \"base_url\": \"http://localhost:11434\"")
            print(f"    - Run: ollama serve")
            print(f"  Option 2: Use Claude API")
            print(f"    - Update provider to 'claude' with your API key")
            print(f"  Option 3: Use LMStudio")
            print(f"    - Update provider to 'lmstudio'")
            dashboard_config = auto_config
            llm_analyzer = None
            print(f"\n[FALLBACK] Using Phase 2 auto-layout")
        except Exception as e:
            print(f"\n[WARN] LLM initialization failed: {type(e).__name__}")
            print(f"[ERROR] {str(e)[:150]}")
            import traceback
            traceback.print_exc()
            dashboard_config = auto_config
            llm_analyzer = None
            print("[FALLBACK] Using Phase 2 auto-layout")
    else:
        dashboard_config = auto_config
        print("\n[INFO] llm_config.json not found - using Phase 2 auto-layout")
        print("[TIP] To enable LLM analysis:")
        print("  1. Create llm_config.json with Ollama configuration")
        print("  2. Start Ollama: ollama serve")
        print("  3. Pull model: ollama pull qwen2.5-coder:14b")

except Exception as e:
    print(f"\n[ERROR] LLM initialization error: {e}")
    dashboard_config = auto_config
    print("[FALLBACK] Using Phase 2 auto-layout")

# Initialize chart analyzer (uses same LLM provider)
chart_analyzer = None
if llm_analyzer is not None and provider is not None:
    try:
        chart_analyzer = ChartAnalyzer(provider, llm_config_obj)
        print("[OK] Chart analyzer initialized for AI-powered chart insights")
    except Exception as e:
        print(f"[WARN] Chart analyzer initialization failed: {e}")
        chart_analyzer = None

# ═══════════════════════════════════════════════════════════════
# PHASE 4: DASH APP LAYOUT (Multi-Page Support)
# ═══════════════════════════════════════════════════════════════

app = Dash(__name__, suppress_callback_exceptions=True, title="Onex AI Data Insight",
           external_stylesheets=[dbc.themes.BOOTSTRAP])

# Pre-populate store data (avoid callback race conditions)
print("\n[INFO] Pre-initializing store data...")
df_json = df.to_json(orient='split')

profiles_dict = {}
for col_name, profile in profiles.items():
    profiles_dict[col_name] = {
        'dtype': profile.dtype,
        'cardinality': profile.cardinality,
        'missing_pct': profile.missing_pct,
        'top_values': profile.top_values,
        'is_temporal': profile.is_temporal,
    }

config_dict = dashboard_config.to_dict() if hasattr(dashboard_config, 'to_dict') else {}

print("[OK] Store data pre-initialized")

NAV_STEPS = [
    ('/upload',    'Upload Data',          '1'),
    ('/',          'Review Data',          '2'),
    ('/config',    'Configure Dashboard',  '3'),
    ('/dashboard', 'Dashboard',            '4'),
]

def make_navbar(active_path='/'):
    """Render the global top navigation bar."""
    nav_items = []
    for path, label, step in NAV_STEPS:
        all_nav_paths = {p for p, _, _ in NAV_STEPS}
        is_active = active_path == path or (path == '/' and active_path not in all_nav_paths)
        nav_items.append(
            dcc.Link(
                html.Div([
                    html.Span(step, style={
                        'width': '20px', 'height': '20px', 'lineHeight': '20px',
                        'borderRadius': '50%', 'textAlign': 'center', 'fontSize': '10px',
                        'fontWeight': '800', 'display': 'inline-block', 'marginRight': '7px',
                        'backgroundColor': '#D4AF37' if is_active else 'rgba(255,255,255,0.25)',
                        'color': '#1A365D' if is_active else '#FFFFFF',
                    }),
                    html.Span(label, style={
                        'fontSize': '13px', 'fontWeight': '600',
                        'color': '#D4AF37' if is_active else 'rgba(255,255,255,0.85)',
                    }),
                ], style={
                    'display': 'flex', 'alignItems': 'center', 'padding': '6px 16px',
                    'borderRadius': '4px',
                    'backgroundColor': 'rgba(255,255,255,0.1)' if is_active else 'transparent',
                }),
                href=path, style={'textDecoration': 'none'}
            )
        )

    return html.Div([
        # Logo + brand
        html.Div([
            html.Div("◆", style={'fontSize': '22px', 'color': '#D4AF37', 'marginRight': '10px'}),
            html.Div([
                html.Div("ONEX AI", style={
                    'fontSize': '13px', 'fontWeight': '800', 'color': '#D4AF37',
                    'letterSpacing': '0.15em', 'lineHeight': '1',
                }),
                html.Div("Data Insight", style={
                    'fontSize': '11px', 'color': 'rgba(255,255,255,0.7)',
                    'letterSpacing': '0.05em', 'lineHeight': '1', 'marginTop': '2px',
                }),
            ]),
        ], style={'display': 'flex', 'alignItems': 'center'}),

        # Nav steps
        html.Div(nav_items, style={'display': 'flex', 'gap': '4px', 'alignItems': 'center'}),
    ], style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'backgroundColor': '#1A365D',
        'padding': '12px 28px',
        'borderBottom': '3px solid #D4AF37',
        'position': 'sticky', 'top': '0', 'zIndex': '1000',
        'boxShadow': '0 2px 12px rgba(0,0,0,0.18)',
    })

# Create multi-page layout with pre-populated data
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),

    # Global navbar (re-rendered by routing callback)
    html.Div(id='global-navbar', children=make_navbar('/')),

    # Client-side session store for persisting user selections
    dcc.Store(id='session-state', storage_type='memory', data={}),
    dcc.Store(id='store-global-dataframe', storage_type='memory', data=df_json),
    dcc.Store(id='store-global-profiles', storage_type='memory', data=profiles_dict),
    dcc.Store(id='store-initial-config', storage_type='memory', data=config_dict),

    # Configuration page stores (shared across pages)
    dcc.Store(id='store-kpi-selections', storage_type='memory', data=[]),
    dcc.Store(id='store-filter-selections', storage_type='memory', data=[]),

    # AI suggestions store — persists across page navigation so dashboard can consume it
    dcc.Store(id='store-ai-suggestions', storage_type='memory', data=None),
    dcc.Store(id='store-objective', storage_type='memory', data=''),
    dcc.Store(id='store-executive-summary', storage_type='memory', data=None),

    # Confirmed data-types store (global so it persists across page transitions)
    dcc.Store(id='store-confirmed-dtypes', storage_type='memory', data={}),

    # Database connector stores
    dcc.Store(id='db-conditions-store', storage_type='memory', data=[]),

    # Page content (no page-level Loading — it would fire for every nested callback
    # like filter dropdowns and chart updates, causing a full-page "refresh" effect.
    # Each section uses its own dcc.Loading instead.)
    html.Div(id='page-content'),
], style={'fontFamily': "'Segoe UI', Arial, sans-serif", 'backgroundColor': '#F7FAFC'})

# ═══════════════════════════════════════════════════════════════
# CALLBACKS - Multi-Page Routing
# ═══════════════════════════════════════════════════════════════

# Update navbar active state on navigation
@app.callback(
    Output('global-navbar', 'children'),
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def update_navbar(pathname):
    return make_navbar(pathname or '/')

# Page routing callback
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    [State('store-global-dataframe', 'data'),
     State('store-global-profiles', 'data'),
     State('store-initial-config', 'data'),
     State('session-state', 'data'),
     State('store-kpi-selections', 'data'),
     State('store-filter-selections', 'data')],
    prevent_initial_call=False
)
def display_page(pathname, df_json, profiles_dict, config_dict, session_data, store_kpi_data, store_filter_data):
    """Route to appropriate page based on URL pathname"""
    # Handle empty pathname
    if not pathname or pathname == '':
        pathname = '/'

    pathname = str(pathname).strip()

    try:
        # Handle initialization - if stores are empty, return error
        if not df_json or not profiles_dict:
            return html.Div(
                [
                    html.H3("Error: Data not initialized"),
                    html.P("The dashboard data failed to initialize. Please refresh the page."),
                ],
                style={'padding': '20px', 'textAlign': 'center', 'color': 'red'}
            )

        # IMPORTANT: Reload data from cache to check for new uploads
        # This ensures uploaded files are used instead of cached store data
        current_df = get_cached_dataframe()
        if current_df is None:
            return html.Div([
                html.H3("Error: Data not loaded"),
                html.P("An error occurred. Check server logs for details."),
            ], style={'padding': '20px', 'color': 'red'})

        current_profiles = load_cached_profiles()
        if not current_profiles:
            return html.Div([
                html.H3("Error: Profiles not available"),
                html.P("An error occurred. Check server logs for details."),
            ], style={'padding': '20px', 'color': 'red'})

        # Get session data
        session_data = session_data or {}
        confirmed_dtypes = session_data.get('confirmed_dtypes', {})

        # If no confirmed dtypes in session, use auto-detected
        if not confirmed_dtypes:
            confirmed_dtypes = {}
            for col, profile_data in current_profiles.items():
                confirmed_dtypes[col] = profile_data.get('dtype', 'categorical')

        # Route based on pathname
        if pathname == '/config':
            result = page_config.generate_config_page(current_df, current_profiles, confirmed_dtypes)
            return result

        elif pathname == '/dashboard':
            # Get KPI and filter selections from session state first, then from stores
            # This allows pre-populated test data to work
            kpi_selections = session_data.get('kpi_selections')
            filter_selections = session_data.get('filter_selections')

            # If session data is empty, try to use pre-populated store data
            if not kpi_selections:
                kpi_selections = store_kpi_data or []
            if not filter_selections:
                filter_selections = store_filter_data or []

            llm_analysis = None
            if config_dict:
                llm_analysis = AnalysisFormatter.format_analysis(
                    type('DashboardConfig', (), config_dict)() if isinstance(config_dict, dict) else config_dict
                )

            result = page_dashboard.generate_dashboard_page(
                current_df,
                kpi_selections=kpi_selections,
                filter_selections=filter_selections,
                confirmed_dtypes=confirmed_dtypes,
                llm_analysis=llm_analysis
            )
            return result

        elif pathname == '/upload':
            return page_upload.generate_upload_page()

        else:  # Default to /data-review
            result = page_data_review.generate_data_review_page(current_df, current_profiles)
            return result

    except Exception as e:
        import traceback
        print(f"[ERROR] display_page callback error: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return html.Div(
            [
                html.H3("Error loading page"),
                html.P("An error occurred. Check server logs for details."),
            ],
            style={'padding': '20px', 'backgroundColor': '#ffeeee', 'color': '#cc0000', 'fontFamily': 'monospace'}
        )


# Callbacks to sync configuration selections to global session state
@app.callback(
    Output('session-state', 'data'),
    [Input('store-kpi-selections', 'data'),
     Input('store-filter-selections', 'data'),
     Input('store-confirmed-dtypes', 'data')],
    [State('session-state', 'data'),
     State('store-objective', 'data')],
    prevent_initial_call=True
)
def sync_config_to_session(kpi_data, filter_data, confirmed_dtypes, session_data, objective_data):
    """Sync configuration page selections to global session state"""
    if session_data is None:
        session_data = {}

    if kpi_data:
        session_data['kpi_selections'] = kpi_data
    if filter_data:
        session_data['filter_selections'] = filter_data
    if confirmed_dtypes:
        session_data['confirmed_dtypes'] = confirmed_dtypes
    if objective_data:
        session_data['objective'] = objective_data

    return session_data

@app.callback(
    Output('store-confirmed-dtypes', 'data'),
    Input({'type': 'dtype-selector', 'index': ALL}, 'value'),
    State({'type': 'dtype-selector', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def save_confirmed_dtypes(dtype_values, selector_ids):
    """Capture dtype overrides from the data-review page into the global store."""
    if not dtype_values or not selector_ids:
        raise dash.exceptions.PreventUpdate
    return {sid['index']: val for sid, val in zip(selector_ids, dtype_values) if val}


# Callbacks are registered within their respective page modules and dashboard_callbacks.py
# Navigation is handled via dcc.Link and href attributes in buttons (see page files)

# ═══════════════════════════════════════════════════════════════
# AI ANALYSIS CALLBACK (Configuration Page)
# ═══════════════════════════════════════════════════════════════

@app.callback(
    Output('ai-analysis-results', 'children'),
    Output('store-ai-suggestions', 'data'),
    Output('kpi-column-selector', 'value'),
    Output('filter-column-selector', 'value'),
    Output('store-executive-summary', 'data'),
    Input('btn-analyze-ai', 'n_clicks'),
    [State('store-kpi-selections', 'data'),
     State('store-filter-selections', 'data'),
     State('store-objective', 'data')],
    running=[(Output('btn-analyze-ai', 'disabled'), True, False),
             (Output('btn-analyze-ai', 'children'), 'Analyzing...', 'Get AI Suggestions')],
    prevent_initial_call=True
)
def analyze_with_ai(n_clicks, kpi_selections, filter_selections, objective):
    """Run LLM analysis — store results, pre-fill selectors, render Big Four report."""
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    # Check if LLM is available FIRST
    if llm_analyzer is None:
        alert = dbc.Alert([
            html.H5("AI Analysis Not Available", style={'marginBottom': '10px', 'color': '#DC2626'}),
            html.P([
                html.Strong("To enable AI analysis: "),
                "Ensure llm_config.json is configured with Ollama/LMStudio/Claude and restart the dashboard.",
            ], style={'marginBottom': '0'})
        ], color="warning", style={'padding': '15px'})
        return alert, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    try:
        print(f"\n[INFO] analyze_with_ai called")

        current_df = get_cached_dataframe()
        if current_df is None:
            return [html.Div("Error: Could not load data for analysis", style={'color': '#DC2626', 'padding': '10px'})]

        current_profiles = load_cached_profiles()

        # ── Build a targeted Big Four analyst prompt ──────────────────────
        col_summary_lines = []
        for col, p in list(current_profiles.items())[:25]:
            dtype  = p.get('dtype', '?')
            card   = p.get('cardinality', 0)
            miss   = round(p.get('missing_pct', 0), 1)
            tops   = ", ".join(str(v) for v in (p.get('top_values') or [])[:3])
            col_summary_lines.append(f"  - {col} [{dtype}] cardinality={card} missing={miss}% top_values=[{tops}]")
        col_summary = "\n".join(col_summary_lines)

        sample_str = current_df.head(5).to_string()

        prompt = build_big_four_prompt(
            col_summary=col_summary,
            sample_str=sample_str,
            n_rows=len(current_df),
            n_cols=len(current_df.columns),
            n_kpis=len(kpi_selections or []),
            n_filters=len(filter_selections or []),
            objective=objective or '',
        )

        print(f"[INFO] Sending Big Four analyst prompt to LLM...")
        raw_response = llm_analyzer.provider.generate_text(prompt)
        print(f"[INFO] LLM response received ({len(raw_response)} chars)")

        # Parse JSON from response
        import re, json as json_mod
        json_match = re.search(r'\{[\s\S]*\}', raw_response)
        if not json_match:
            raise ValueError("No JSON object found in LLM response")
        result = json_mod.loads(json_match.group())

        # ── Render Big Four consulting panel ─────────────────────────────
        NAVY = '#1A365D'
        GOLD = '#D4AF37'
        from core.config import TEXT, TEXT_LIGHT, BORDER

        def badge(text, color='#1A365D', bg='#EBF4FF'):
            return html.Span(text, style={
                'fontSize': '10px', 'fontWeight': '700', 'padding': '2px 8px',
                'borderRadius': '10px', 'color': color, 'backgroundColor': bg,
                'border': f'1px solid {color}33', 'marginRight': '6px', 'whiteSpace': 'nowrap',
            })

        TH = {
            'fontSize': '10px', 'fontWeight': '700', 'textTransform': 'uppercase',
            'letterSpacing': '0.07em', 'padding': '8px 12px',
            'backgroundColor': NAVY, 'color': '#FFFFFF', 'borderBottom': f'2px solid {GOLD}',
        }
        TD = {'fontSize': '12px', 'padding': '8px 12px', 'borderBottom': f'1px solid {BORDER}', 'verticalAlign': 'top'}

        sections = []

        # Header
        sections.append(html.Div([
            html.Span("AI ANALYSIS REPORT", style={
                'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.12em',
                'color': GOLD, 'display': 'block', 'marginBottom': '4px',
            }),
            html.Div("Senior Data Analytics Assessment", style={
                'fontSize': '16px', 'fontWeight': '700', 'color': '#FFFFFF',
            }),
            html.Div(f"{len(current_df):,} records · {len(current_df.columns)} columns analysed",
                     style={'fontSize': '12px', 'color': 'rgba(255,255,255,0.6)', 'marginTop': '4px'}),
        ], style={
            'backgroundColor': NAVY, 'padding': '16px 20px',
            'borderRadius': '8px 8px 0 0', 'borderBottom': f'3px solid {GOLD}',
        }))

        # Executive Findings
        findings = result.get('executive_findings', [])
        dq_score = result.get('data_quality_score', 0.85)
        if findings:
            finding_els = []
            for i, f in enumerate(findings, 1):
                finding_els.append(html.Div([
                    html.Span(f"0{i}", style={
                        'fontSize': '11px', 'fontWeight': '800', 'color': NAVY,
                        'backgroundColor': '#D4AF3722', 'borderRadius': '50%',
                        'width': '22px', 'height': '22px', 'lineHeight': '22px',
                        'textAlign': 'center', 'display': 'inline-block',
                        'marginRight': '10px', 'flexShrink': '0',
                    }),
                    html.Span(f, style={'fontSize': '13px', 'color': TEXT, 'lineHeight': '1.6'}),
                ], style={'display': 'flex', 'alignItems': 'flex-start', 'marginBottom': '10px'}))

            dq_color = '#16A34A' if dq_score >= 0.85 else '#D97706' if dq_score >= 0.65 else '#DC2626'
            sections.append(html.Div([
                html.Div([
                    html.Div("Executive Findings", style={
                        'fontWeight': '700', 'fontSize': '13px', 'color': NAVY,
                        'textTransform': 'uppercase', 'letterSpacing': '0.06em',
                    }),
                    html.Span(f"Data Quality: {int(dq_score*100)}%", style={
                        'fontSize': '11px', 'fontWeight': '700', 'color': dq_color,
                        'backgroundColor': f'{dq_color}15', 'padding': '2px 8px',
                        'borderRadius': '10px', 'border': f'1px solid {dq_color}44',
                    }),
                ], style={'display': 'flex', 'justifyContent': 'space-between',
                          'alignItems': 'center', 'marginBottom': '12px'}),
                html.Div(finding_els),
            ], style={'padding': '16px 20px', 'backgroundColor': '#F8FAFF',
                      'borderBottom': f'1px solid {BORDER}'}))

        # KPI Recommendations
        kpis = result.get('kpis', [])
        if kpis:
            rows = []
            for k in kpis:
                col_val = k.get('column', '')
                agg_val = k.get('aggregation', 'sum').upper()
                label_val = k.get('label', col_val)
                why = k.get('rationale', '—')
                agg_colors = {'SUM': ('#065F46', '#D1FAE5'), 'MEAN': ('#1E40AF', '#DBEAFE'),
                              'COUNT': ('#7C2D12', '#FED7AA'), 'MAX': ('#4C1D95', '#EDE9FE')}
                ac, ab = agg_colors.get(agg_val, ('#374151', '#F3F4F6'))
                rows.append(html.Tr([
                    html.Td(html.Span(label_val, style={'fontWeight': '600', 'color': NAVY, 'fontSize': '12px'}), style={**TD, 'backgroundColor': '#F8FAFF'}),
                    html.Td(html.Code(col_val, style={'fontSize': '11px', 'color': '#374151', 'backgroundColor': '#F1F5F9', 'padding': '2px 6px', 'borderRadius': '3px'}), style={**TD, 'backgroundColor': '#FFFFFF'}),
                    html.Td(badge(agg_val, ac, ab), style={**TD, 'backgroundColor': '#F8FAFF'}),
                    html.Td(why, style={**TD, 'color': TEXT_LIGHT, 'fontSize': '11px', 'backgroundColor': '#FFFFFF'}),
                ]))

            sections.append(html.Div([
                html.Div("Recommended KPIs", style={
                    'fontWeight': '700', 'fontSize': '13px', 'color': NAVY,
                    'textTransform': 'uppercase', 'letterSpacing': '0.06em', 'marginBottom': '10px',
                }),
                html.Div(html.Table([
                    html.Thead(html.Tr([html.Th(h, style=TH) for h in ['Label', 'Column', 'Aggregation', 'Why It Matters']])),
                    html.Tbody(rows),
                ], style={'width': '100%', 'borderCollapse': 'collapse', 'border': f'1px solid {BORDER}'}),
                style={'overflowX': 'auto'}),
            ], style={'padding': '16px 20px', 'backgroundColor': '#FFFFFF',
                      'borderBottom': f'1px solid {BORDER}'}))

        # Chart Recommendations
        charts = result.get('charts', [])
        if charts:
            chart_type_colors = {
                'bar': ('#1A365D', '#EBF4FF'), 'pie': ('#065F46', '#D1FAE5'),
                'line': ('#7C3AED', '#EDE9FE'), 'histogram': ('#92400E', '#FEF3C7'),
                'box': ('#9D174D', '#FCE7F3'), 'heatmap': ('#1E40AF', '#DBEAFE'),
                'funnel': ('#065F46', '#D1FAE5'), 'treemap': ('#B45309', '#FEF3C7'),
                'scatter': ('#4C1D95', '#EDE9FE'),
            }
            rows = []
            for i, c in enumerate(charts):
                ct = c.get('type', 'bar').lower()
                cc, cb = chart_type_colors.get(ct, ('#374151', '#F3F4F6'))
                rows.append(html.Tr([
                    html.Td(badge(ct.upper(), cc, cb), style={**TD, 'backgroundColor': '#F8FAFF' if i%2==0 else '#FFFFFF'}),
                    html.Td(html.Strong(c.get('title', '—'), style={'color': NAVY, 'fontSize': '12px'}),
                            style={**TD, 'backgroundColor': '#F8FAFF' if i%2==0 else '#FFFFFF'}),
                    html.Td([
                        html.Code(c.get('x', ''), style={'fontSize': '10px', 'backgroundColor': '#F1F5F9', 'padding': '1px 5px', 'borderRadius': '3px', 'marginRight': '4px'}),
                        html.Span('→', style={'color': TEXT_LIGHT, 'marginRight': '4px'}),
                        html.Code(c.get('y', ''), style={'fontSize': '10px', 'backgroundColor': '#F1F5F9', 'padding': '1px 5px', 'borderRadius': '3px'}),
                    ], style={**TD, 'backgroundColor': '#F8FAFF' if i%2==0 else '#FFFFFF'}),
                    html.Td(c.get('rationale', '—'), style={**TD, 'color': TEXT_LIGHT, 'fontSize': '11px', 'backgroundColor': '#F8FAFF' if i%2==0 else '#FFFFFF'}),
                ]))

            sections.append(html.Div([
                html.Div("Chart Blueprint", style={
                    'fontWeight': '700', 'fontSize': '13px', 'color': NAVY,
                    'textTransform': 'uppercase', 'letterSpacing': '0.06em', 'marginBottom': '10px',
                }),
                html.Div(html.Table([
                    html.Thead(html.Tr([html.Th(h, style=TH) for h in ['Type', 'Business Title', 'Axes (X → Y)', 'Analytical Rationale']])),
                    html.Tbody(rows),
                ], style={'width': '100%', 'borderCollapse': 'collapse', 'border': f'1px solid {BORDER}'}),
                style={'overflowX': 'auto'}),
            ], style={'padding': '16px 20px', 'backgroundColor': '#FAFBFC',
                      'borderBottom': f'1px solid {BORDER}'}))

        # Filters
        filters = result.get('filters', [])
        if filters:
            filter_badges = [
                html.Div([
                    html.Div(f.get('label', f.get('column', '—')), style={
                        'fontWeight': '700', 'fontSize': '12px', 'color': NAVY,
                    }),
                    html.Div(f.get('rationale', ''), style={
                        'fontSize': '11px', 'color': TEXT_LIGHT, 'marginTop': '2px',
                    }),
                    html.Code(f.get('column', ''), style={
                        'fontSize': '10px', 'color': '#374151', 'backgroundColor': '#F1F5F9',
                        'padding': '1px 5px', 'borderRadius': '3px', 'marginTop': '4px', 'display': 'block',
                    }),
                ], style={
                    'backgroundColor': '#EBF4FF', 'border': f'1px solid #BFDBFE',
                    'borderLeft': f'3px solid {NAVY}', 'borderRadius': '4px',
                    'padding': '10px 14px', 'flex': '1', 'minWidth': '180px',
                })
                for f in filters
            ]
            sections.append(html.Div([
                html.Div("Recommended Drill-Down Filters", style={
                    'fontWeight': '700', 'fontSize': '13px', 'color': NAVY,
                    'textTransform': 'uppercase', 'letterSpacing': '0.06em', 'marginBottom': '10px',
                }),
                html.Div(filter_badges, style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'}),
            ], style={'padding': '16px 20px', 'backgroundColor': '#FFFFFF',
                      'borderBottom': f'1px solid {BORDER}'}))

        # Narrative footer
        narrative = result.get('narrative', '')
        if narrative:
            sections.append(html.Div([
                html.Span("STRATEGIC NARRATIVE", style={
                    'fontSize': '9px', 'fontWeight': '800', 'letterSpacing': '0.12em',
                    'color': GOLD, 'display': 'block', 'marginBottom': '8px',
                }),
                html.P(narrative, style={
                    'fontSize': '13px', 'color': TEXT, 'lineHeight': '1.7',
                    'margin': '0', 'fontStyle': 'italic',
                }),
            ], style={
                'padding': '16px 20px', 'backgroundColor': '#F1F5F9',
                'borderTop': f'2px solid {GOLD}', 'borderRadius': '0 0 8px 8px',
            }))

        visual_panel = html.Div(sections, style={
            'border': f'1px solid {BORDER}', 'borderRadius': '8px',
            'boxShadow': '0 4px 20px rgba(0,0,0,0.08)', 'overflow': 'hidden',
            'marginTop': '8px',
        })

        # ── Extract selector values to pre-fill config page ──────────────
        valid_cols = set(current_df.columns)

        ai_kpi_cols = [
            k['column'] for k in result.get('kpis', [])
            if isinstance(k, dict) and k.get('column') in valid_cols
        ]
        ai_filter_cols = [
            f['column'] for f in result.get('filters', [])
            if isinstance(f, dict) and f.get('column') in valid_cols
        ]

        # ── Build store payload for dashboard chart generation ────────────
        ai_store = {
            'charts': [
                c for c in result.get('charts', [])
                if isinstance(c, dict)
                   and c.get('x', '') in valid_cols
                   # y may be empty for count-only charts — allow it
            ],
            'kpis': result.get('kpis', []),
            'filters': result.get('filters', []),
            'narrative': result.get('narrative', ''),
        }
        exec_summary_data = result.get('executive_summary', None)
        # Attach data_quality_score — normalise from LLM's 0–100 range to 0.0–1.0
        raw_dq = result.get('data_quality_score', 0.85)
        dq = float(raw_dq) if raw_dq else 0.85
        if dq > 1.0:
            dq = dq / 100.0
        dq = max(0.0, min(1.0, dq))
        if exec_summary_data and isinstance(exec_summary_data, dict):
            exec_summary_data['data_quality_score'] = dq
        print(f"[AI] Storing {len(ai_store['charts'])} charts, {len(ai_kpi_cols)} KPI cols, {len(ai_filter_cols)} filter cols")

        return visual_panel, ai_store, ai_kpi_cols or dash.no_update, ai_filter_cols or dash.no_update, exec_summary_data

    except Exception as e:
        import traceback
        print(f"[ERROR] analyze_with_ai: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        err_el = html.Div([
            html.Strong("Analysis failed. "),
            html.Span("Check server logs for details."),
        ], style={'color': '#DC2626', 'padding': '12px', 'background': '#FEE2E2',
                  'borderRadius': '6px', 'fontSize': '13px'})
        return err_el, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# ═══════════════════════════════════════════════════════════════
# REFRESH ANALYSIS BUTTON (Dashboard page)
# ═══════════════════════════════════════════════════════════════

@app.callback(
    Output('store-llm-analysis', 'data'),
    Input('btn-refresh-analysis', 'n_clicks'),
    State('store-objective', 'data'),
    prevent_initial_call=True
)
def refresh_dashboard_analysis(n_clicks, objective):
    """Re-run LLM analysis and update the dashboard store when Refresh is clicked."""
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    if llm_analyzer is None:
        raise dash.exceptions.PreventUpdate
    try:
        current_df = get_cached_dataframe()
        current_profiles = load_cached_profiles()
        if current_df is None:
            raise dash.exceptions.PreventUpdate
        objective = (objective or '').strip()[:500]
        objective_note = f" User objective: {objective}" if objective else ""
        user_context = f"Dataset contains {len(current_df):,} records. Refresh requested by user.{objective_note}"
        result = llm_analyzer.analyze(current_df, current_profiles, user_context)
        if result and hasattr(result, 'to_dict'):
            return result.to_dict()
        return None
    except Exception as e:
        print(f"[WARN] refresh_dashboard_analysis failed: {e}")
        raise dash.exceptions.PreventUpdate

# ═══════════════════════════════════════════════════════════════
# DASHBOARD SAVE / LOAD CALLBACKS
# ═══════════════════════════════════════════════════════════════

@app.callback(
    Output('save-load-modal', 'is_open'),
    Input('btn-open-save-modal', 'n_clicks'),
    State('save-load-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_save_modal(n, is_open):
    return not is_open if n else is_open


@app.callback(
    Output('save-dashboard-status', 'children'),
    Input('btn-save-dashboard', 'n_clicks'),
    State('save-dashboard-name', 'value'),
    State('store-kpi-selections', 'data'),
    State('store-filter-selections', 'data'),
    State('store-confirmed-dtypes', 'data'),
    State('store-ai-suggestions', 'data'),
    prevent_initial_call=True
)
def cb_save_dashboard(n_clicks, name, kpis, filters, dtypes, ai_sugg):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    try:
        label = (name or '').strip() or 'My Dashboard'
        path = save_dashboard(label, kpis or [], filters or [], dtypes or {}, ai_sugg or {})
        fname = os.path.basename(path)
        return html.Span(f"✓ Saved as '{fname}'", style={'color': '#16A34A', 'fontSize': '12px'})
    except Exception as e:
        print(f"[ERROR] save_dashboard: {e}")
        return html.Span("Save failed — check server logs", style={'color': '#DC2626', 'fontSize': '12px'})


@app.callback(
    Output('load-dashboard-dropdown', 'options'),
    Input('btn-refresh-saved-list', 'n_clicks'),
    Input('save-dashboard-status', 'children'),  # refresh list after save
    prevent_initial_call=False
)
def cb_refresh_saved_list(n_clicks, _save_trigger):
    saved = list_saved()
    return [{'label': f"{s['name']} ({s['saved_at'][:16]})", 'value': s['path']} for s in saved]


@app.callback(
    Output('store-kpi-selections', 'data', allow_duplicate=True),
    Output('store-filter-selections', 'data', allow_duplicate=True),
    Output('store-confirmed-dtypes', 'data', allow_duplicate=True),
    Output('store-ai-suggestions', 'data', allow_duplicate=True),
    Output('load-dashboard-status', 'children'),
    Input('btn-load-dashboard', 'n_clicks'),
    State('load-dashboard-dropdown', 'value'),
    prevent_initial_call=True
)
def cb_load_dashboard(n_clicks, path):
    if not n_clicks or not path:
        raise dash.exceptions.PreventUpdate
    data = load_dashboard(path)
    if not data:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, \
               html.Span("Load failed", style={'color': '#DC2626', 'fontSize': '12px'})
    msg = html.Span(f"✓ Loaded '{data.get('name', '')}'", style={'color': '#16A34A', 'fontSize': '12px'})
    return (data.get('kpi_selections', []), data.get('filter_selections', []),
            data.get('confirmed_dtypes', {}), data.get('ai_suggestions', {}), msg)


# ═══════════════════════════════════════════════════════════════
# DATABASE CONNECTOR CALLBACKS
# ═══════════════════════════════════════════════════════════════

_DB_DEFAULT_PORTS = {
    'postgresql': 5432, 'mysql': 3306, 'mssql': 1433,
    'oracle': 1521, 'sqlite': None,
}


@app.callback(
    Output('db-port', 'value'),
    Input('db-type-dropdown', 'value'),
    prevent_initial_call=True
)
def auto_db_port(db_type):
    return _DB_DEFAULT_PORTS.get(db_type or 'postgresql')


@app.callback(
    Output('db-connection-status', 'children'),
    Output('db-table-section', 'style'),
    Output('db-table-dropdown', 'options'),
    Input('btn-test-db', 'n_clicks'),
    State('db-type-dropdown', 'value'),
    State('db-host', 'value'),
    State('db-port', 'value'),
    State('db-name', 'value'),
    State('db-username', 'value'),
    State('db-password', 'value'),
    prevent_initial_call=True
)
def cb_test_db_connection(n_clicks, db_type, host, port, db_name, username, password):
    hide = {'display': 'none'}
    show = {'display': 'block'}
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    try:
        effective_port = port or _DB_DEFAULT_PORTS.get(db_type or 'postgresql')
        engine = db_connector.connect(db_type, host, effective_port, db_name, username, password)
        ok, msg = db_connector.test_connection(engine)
        if ok:
            tables = db_connector.list_tables(engine)
            _current_db['engine'] = engine
            _current_db['db_type'] = db_type
            table_opts = [{'label': t, 'value': t} for t in tables]
            status = html.Span(
                f"✓ Connected — {len(tables)} table(s) found",
                style={'color': '#16A34A', 'fontWeight': '600', 'fontSize': '13px'},
            )
            return status, show, table_opts
        print(f"[db] test_connection failed: {msg}")
        return (
            html.Span("✗ Connection failed. Check server logs.", style={'color': '#DC2626', 'fontSize': '13px'}),
            hide, [],
        )
    except Exception as e:
        print(f"[ERROR] cb_test_db_connection: {e}")
        return (
            html.Span("Connection error. Check server logs.", style={'color': '#DC2626', 'fontSize': '13px'}),
            hide, [],
        )


@app.callback(
    Output('db-conditions-store', 'data'),
    Input('btn-add-where', 'n_clicks'),
    Input({'type': 'btn-remove-where', 'index': ALL}, 'n_clicks'),
    State('db-conditions-store', 'data'),
    prevent_initial_call=True
)
def update_where_conditions(add_clicks, remove_clicks, conditions):
    conditions = list(conditions or [])
    triggered_id = dash.ctx.triggered_id
    if triggered_id == 'btn-add-where':
        conditions.append({})
    elif isinstance(triggered_id, dict) and triggered_id.get('type') == 'btn-remove-where':
        idx = triggered_id.get('index')
        if idx is not None and 0 <= idx < len(conditions):
            conditions = [c for i, c in enumerate(conditions) if i != idx]
    return conditions


@app.callback(
    Output('where-conditions-container', 'children'),
    Input('db-conditions-store', 'data'),
)
def render_where_conditions(conditions):
    from core.config import BORDER, TEXT
    if not conditions:
        return []
    op_options = [{'label': op, 'value': op} for op in ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN']]
    input_style = {
        'padding': '6px 8px', 'borderRadius': '4px',
        'border': f'1px solid {BORDER}', 'fontSize': '12px',
    }
    rows = []
    for i in range(len(conditions)):
        rows.append(html.Div([
            dcc.Input(
                id={'type': 'db-cond-col', 'index': i},
                type='text', placeholder='column_name',
                style={**input_style, 'flex': '2', 'minWidth': '100px'},
            ),
            dcc.Dropdown(
                id={'type': 'db-cond-op', 'index': i},
                options=op_options, value='=', clearable=False,
                style={'flex': '1', 'minWidth': '70px', 'fontSize': '12px'},
            ),
            dcc.Input(
                id={'type': 'db-cond-val', 'index': i},
                type='text', placeholder='value',
                style={**input_style, 'flex': '2', 'minWidth': '100px'},
            ),
            dbc.Button(
                "×",
                id={'type': 'btn-remove-where', 'index': i},
                size='sm', color='danger', outline=True,
                style={'flexShrink': '0', 'padding': '4px 10px', 'fontSize': '14px', 'lineHeight': '1'},
            ),
        ], style={'display': 'flex', 'gap': '8px', 'alignItems': 'center', 'marginBottom': '8px'}))
    return rows


@app.callback(
    Output('db-fetch-status', 'children'),
    Output('url', 'pathname', allow_duplicate=True),
    Input('btn-fetch-db', 'n_clicks'),
    State('db-table-dropdown', 'value'),
    State('db-row-limit', 'value'),
    State({'type': 'db-cond-col', 'index': ALL}, 'value'),
    State({'type': 'db-cond-op', 'index': ALL}, 'value'),
    State({'type': 'db-cond-val', 'index': ALL}, 'value'),
    running=[
        (Output('btn-fetch-db', 'disabled'), True, False),
        (Output('btn-fetch-db', 'children'), 'Fetching…', 'Fetch Data →'),
    ],
    prevent_initial_call=True
)
def cb_fetch_db(n_clicks, table, limit, cond_cols, cond_ops, cond_vals):
    from core.cache_manager import CacheManager
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    if not table:
        return html.Span("Select a table first.", style={'color': '#DC2626', 'fontSize': '13px'}), dash.no_update
    engine = _current_db.get('engine')
    db_type = _current_db.get('db_type', 'postgresql')
    if engine is None:
        return html.Span("No active connection. Test connection first.", style={'color': '#DC2626', 'fontSize': '13px'}), dash.no_update
    try:
        # Build WHERE conditions from dynamic rows (skip incomplete rows)
        conditions = []
        for col, op, val in zip(cond_cols or [], cond_ops or [], cond_vals or []):
            if col and col.strip() and val is not None and str(val).strip():
                conditions.append({'column': col.strip(), 'operator': op or '=', 'value': str(val).strip()})
        where_str, params = query_builder.build(conditions)

        row_limit = int(limit or 100_000)
        df = db_connector.fetch(engine, table, where_str, params, row_limit, db_type)

        if df.empty:
            return html.Span(
                "Query returned 0 rows. Check table selection and WHERE conditions.",
                style={'color': '#D97706', 'fontSize': '13px'},
            ), dash.no_update

        # Save to cache exactly like an upload so the rest of the app can consume it
        upload_id, _profiles = CacheManager.save_upload(df, f"db:{table}")
        print(f"[db] Fetched {len(df):,} rows from {table} → cached as {upload_id}")

        return (
            html.Span(f"✓ {len(df):,} rows fetched from '{table}'", style={'color': '#16A34A', 'fontSize': '13px'}),
            '/data-review',
        )
    except Exception as e:
        import traceback
        print(f"[ERROR] cb_fetch_db: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return html.Span("Fetch failed. Check server logs.", style={'color': '#DC2626', 'fontSize': '13px'}), dash.no_update


# ═══════════════════════════════════════════════════════════════
# REGISTER DASHBOARD-SPECIFIC CALLBACKS
# ═══════════════════════════════════════════════════════════════

# Register callbacks for the dashboard page
register_dashboard_callbacks(app, get_cached_dataframe, chart_analyzer)


# ═══════════════════════════════════════════════════════════════
# CLIENTSIDE CALLBACKS
# ═══════════════════════════════════════════════════════════════

app.clientside_callback(
    """
    function(n) {
        if (n) {
            setTimeout(function() { window.print(); }, 200);
        }
        return n;
    }
    """,
    Output('btn-download-pdf', 'n_clicks'),
    Input('btn-download-pdf', 'n_clicks'),
    prevent_initial_call=True
)


# ═══════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY CALLBACK
# ═══════════════════════════════════════════════════════════════

@app.callback(
    Output('executive-summary-container', 'children'),
    Input('store-executive-summary', 'data'),
    Input('store-llm-analysis', 'data'),
    prevent_initial_call=False
)
def update_executive_summary(exec_data, llm_data):
    from core.components import executive_summary_card

    # Priority: AI suggestions executive summary > startup LLM analysis
    summary = exec_data or {}
    if not summary and llm_data and isinstance(llm_data, dict):
        # Try startup LLM analysis structure
        raw = llm_data.get('executive_summary', {})
        if raw:
            summary = raw

    if not summary:
        return executive_summary_card(
            title="Executive Summary",
            findings=["Run 'Get AI Suggestions' on the Configure page for an AI-generated executive brief."],
            health_score=0.85,
            status='caution',
        )

    key_findings = summary.get('key_findings', [])
    narrative = summary.get('narrative', '')
    risk_flags = summary.get('risk_flags', [])
    priority_action = summary.get('priority_action', '')
    raw_score = summary.get('data_quality_score',
                            exec_data.get('data_quality_score', 0.85) if exec_data else 0.85)
    score = float(raw_score) if raw_score else 0.85
    if score > 1.0:
        score = score / 100.0  # LLM sometimes returns 0–100 instead of 0.0–1.0
    score = max(0.0, min(1.0, score))

    return executive_summary_card(
        title="Executive Summary",
        findings=key_findings,
        health_score=score,
        status='healthy' if score > 0.8 else 'caution',
        narrative=narrative,
        risk_flags=risk_flags,
        priority_action=priority_action,
    )


# ═══════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("[START] Dashboard starting at http://0.0.0.0:8050")
    print("="*60)
    print("\nPages:")
    print("  [OK] /data-review - Confirm detected data types")
    print("  [OK] /config - Select KPIs, filters, and aggregations")
    print("  [OK] /dashboard - Interactive dashboard with user selections")
    print("\nFeatures:")
    print("  [OK] Phase 1: Modular code architecture")
    print("  [OK] Phase 2: Auto-analysis & intelligent layout")
    print("  [OK] Phase 3: LLM integration (Ollama/LMStudio/Claude)")
    print("  [OK] Phase 4: Multi-page interactive dashboard")
    print("\n")
app.run(host="0.0.0.0", port=8050, debug=True)
#    app.run(debug=True, port=8050)
