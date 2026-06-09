# Dashboard Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-supplied Objective field to AI analysis, fix performance and security issues, delete 14 stale files, and consolidate all documentation into a single manual.

**Architecture:** The Objective textarea lives in the AI Suggestions card on the config page, synced to a session-scoped `dcc.Store`. The Big Four LLM prompt moves from inline `dashboard.py` into `llm/prompts.py` as `build_big_four_prompt()`, which accepts an `objective` parameter. All other changes are targeted fixes with no structural reorganisation.

**Tech Stack:** Python 3.x, Dash 2.x, Plotly, Pandas, dash-bootstrap-components, pytest

---

## File Map

| File | Action | What changes |
|---|---|---|
| `test_callbacks.py`, `test_plot.py`, `test_system.py`, `test_dashboard_init.py`, `test_llm_improvement.py` | **Delete** | Stale test files |
| `IMPLEMENTATION_SUMMARY.md`, `IMPLEMENTATION_CHECKLIST.md`, `IMPROVEMENTS.md`, `TEST_RESULTS.md`, `FIX_SUMMARY.md`, `TRANSFORMATION_SUMMARY.md`, `OLLAMA_TROUBLESHOOTING.md` | **Delete** | Stale docs consolidated into manual |
| `D:testpages__init__.py`, `D:testTEST_CHECKLIST.md`, `D:testLLM_DATA_PRIVACY.md` | **Delete** | Malformed filenames |
| `dashboard.py` | **Modify** | Remove unused imports, fix duplicate docstring, fix `provider` init, remove inline prompt, add `store-objective`, wire objective into callbacks, fix error handlers, fix coercion at startup |
| `core/config.py` | **Modify** | Remove `CONFIG_DIR` from makedirs loop |
| `llm/prompts.py` | **Modify** | Add `build_big_four_prompt()` function |
| `pages/page_config.py` | **Modify** | Add Objective textarea + sync callback |
| `tests/test_prompts.py` | **Create** | Tests for `build_big_four_prompt()` |
| `docs/ONEX_AI_DASHBOARD_GUIDE.md` | **Create** | Single comprehensive manual |
| `CLAUDE.md` | **Modify** | Remove stale sections, add Objective field docs |
| Memory files (3) | **Modify** | Update project state and add error-handling rule |

---

## Task 1: Delete stale files

**Files:** Delete 14 files.

- [ ] **Step 1: Delete test files**

```bash
cd D:/test
rm test_callbacks.py test_plot.py test_system.py test_dashboard_init.py test_llm_improvement.py
```

- [ ] **Step 2: Delete stale markdown docs**

```bash
rm IMPLEMENTATION_SUMMARY.md IMPLEMENTATION_CHECKLIST.md IMPROVEMENTS.md TEST_RESULTS.md FIX_SUMMARY.md TRANSFORMATION_SUMMARY.md OLLAMA_TROUBLESHOOTING.md
```

- [ ] **Step 3: Delete malformed files**

List them first to confirm they exist:
```bash
ls D:/test/D:test* 2>/dev/null
```
Then delete:
```bash
rm "D:/test/D:testpages__init__.py" "D:/test/D:testTEST_CHECKLIST.md" "D:/test/D:testLLM_DATA_PRIVACY.md" 2>/dev/null || echo "some already gone"
```

- [ ] **Step 4: Verify dashboard still imports cleanly**

```bash
cd D:/test && python -c "import dashboard; print('[OK] imports clean')"
```
Expected: `[OK] imports clean` (startup logs will appear too — that is normal).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: delete 14 stale test and doc files"
```

---

## Task 2: Fix redundant code in `dashboard.py` and `core/config.py`

**Files:**
- Modify: `dashboard.py`
- Modify: `core/config.py`

- [ ] **Step 1: Remove duplicate docstring from `display_page` in `dashboard.py`**

Find lines 495-503. The function has two identical docstrings back-to-back. Remove the second one (line 502):

```python
# BEFORE:
def display_page(pathname, df_json, profiles_dict, config_dict, session_data, store_kpi_data, store_filter_data):
    """Route to appropriate page based on URL pathname"""
    if not pathname or pathname == '':
        pathname = '/'
    pathname = str(pathname).strip()
    """Route to appropriate page based on URL pathname"""   # DELETE this line

# AFTER:
def display_page(pathname, df_json, profiles_dict, config_dict, session_data, store_kpi_data, store_filter_data):
    """Route to appropriate page based on URL pathname"""
    if not pathname or pathname == '':
        pathname = '/'
    pathname = str(pathname).strip()
```

- [ ] **Step 2: Remove unused imports from `dashboard.py`**

In the imports block (lines 37-48), remove two unused symbols:

```python
# BEFORE line 38:
from core.components import kpi_card, filter_control, chart_container, section_header
# AFTER:
from core.components import kpi_card, filter_control, chart_container

# BEFORE line 47 (delete the whole line):
from callbacks.chart_callbacks import register_chart_callbacks
# AFTER: (line removed entirely)
```

- [ ] **Step 3: Fix `provider` variable initialisation in `dashboard.py`**

Around line 235, move `provider = None` up to sit beside the other `None` initialisations, before any `try` block:

```python
# BEFORE:
llm_config = None
llm_config_obj = None
llm_analyzer = None
dashboard_config = auto_config

try:
    ...
    if llm_config_path:
        ...
        provider = None  # Initialize to None to avoid NameError if exception occurs

# AFTER:
llm_config = None
llm_config_obj = None
llm_analyzer = None
provider = None          # always defined — used at line 349
dashboard_config = auto_config

try:
    ...
    if llm_config_path:
        ...
        # remove the old inline "provider = None" line from inside the try block
```

- [ ] **Step 4: Remove `CONFIG_DIR` from makedirs loop in `core/config.py`**

```python
# BEFORE (around line 110):
for d in [OUTPUT_DIR, CONFIG_DIR, UPLOAD_DIR]:
    os.makedirs(d, exist_ok=True)

# AFTER:
for d in [OUTPUT_DIR, UPLOAD_DIR]:
    os.makedirs(d, exist_ok=True)
```

- [ ] **Step 5: Verify imports still clean**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```

- [ ] **Step 6: Commit**

```bash
git add dashboard.py core/config.py
git commit -m "refactor: remove unused imports, duplicate docstring, and dead CONFIG_DIR creation"
```

---

## Task 3: Move Big Four prompt to `llm/prompts.py`

**Files:**
- Modify: `llm/prompts.py`
- Create: `tests/__init__.py`, `tests/test_prompts.py`
- Modify: `dashboard.py`

- [ ] **Step 1: Create test file (TDD — write test before implementation)**

```bash
mkdir -p D:/test/tests && touch D:/test/tests/__init__.py
```

Create `tests/test_prompts.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from llm.prompts import build_big_four_prompt


def test_prompt_contains_required_sections():
    result = build_big_four_prompt(
        col_summary="  - Amount [numeric] cardinality=500 missing=0% top_values=[1000, 2000]",
        sample_str="Amount\n1000\n2000",
        n_rows=1000, n_cols=5, n_kpis=2, n_filters=1
    )
    assert "McKinsey" in result
    assert "COLUMN PROFILES" in result
    assert "SAMPLE DATA" in result
    assert "executive_findings" in result
    assert "USER OBJECTIVE" not in result


def test_prompt_with_objective_prepends_goal():
    result = build_big_four_prompt(
        col_summary="  - Amount [numeric] cardinality=500 missing=0% top_values=[1000]",
        sample_str="Amount\n1000",
        n_rows=500, n_cols=3, n_kpis=1, n_filters=1,
        objective="Check monthly trend of expense"
    )
    assert result.startswith("USER OBJECTIVE:")
    assert "Check monthly trend of expense" in result
    assert "McKinsey" in result


def test_prompt_objective_truncated_at_500_chars():
    long_objective = "x" * 600
    result = build_big_four_prompt(
        col_summary="col [numeric]",
        sample_str="col\n1",
        n_rows=10, n_cols=1, n_kpis=0, n_filters=0,
        objective=long_objective
    )
    injected = result.split("USER OBJECTIVE:")[1].split("\n")[0].strip()
    assert len(injected) <= 500


def test_prompt_empty_objective_ignored():
    result = build_big_four_prompt(
        col_summary="col [numeric]",
        sample_str="col\n1",
        n_rows=10, n_cols=1, n_kpis=0, n_filters=0,
        objective=""
    )
    assert "USER OBJECTIVE" not in result


def test_prompt_whitespace_objective_ignored():
    result = build_big_four_prompt(
        col_summary="col [numeric]",
        sample_str="col\n1",
        n_rows=10, n_cols=1, n_kpis=0, n_filters=0,
        objective="   "
    )
    assert "USER OBJECTIVE" not in result
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd D:/test && python -m pytest tests/test_prompts.py -v
```
Expected: `AttributeError: module 'llm.prompts' has no attribute 'build_big_four_prompt'`

- [ ] **Step 3: Add `build_big_four_prompt()` to the end of `llm/prompts.py`**

```python


def build_big_four_prompt(col_summary: str, sample_str: str, n_rows: int,
                           n_cols: int, n_kpis: int, n_filters: int,
                           objective: str = '') -> str:
    """Build the Big Four analyst prompt, optionally scoped to a user objective."""
    objective = (objective or '').strip()[:500].strip()

    objective_section = ''
    if objective:
        objective_section = (
            f'USER OBJECTIVE: {objective}\n\n'
            f'Use this objective to prioritise chart types, KPI selection, and the strategic narrative.\n'
            f'Focus your recommendations on answering: "{objective}"\n\n'
        )

    return f"""{objective_section}You are a Senior Data Analytics Partner at McKinsey & Company with 15 years of experience turning raw data into C-suite insights. A client has just shared their dataset and needs your expert analysis.

DATASET OVERVIEW:
- Rows: {n_rows:,}  |  Columns: {n_cols}
- User has pre-selected {n_kpis} KPIs and {n_filters} filters

COLUMN PROFILES (name [type] cardinality missing% top_values):
{col_summary}

SAMPLE DATA (5 rows):
{sample_str}

INSTRUCTIONS:
As a Big Four senior analyst, provide a rigorous, specific, and actionable diagnostic. Do NOT be generic.

1. EXECUTIVE FINDINGS (3-4 bullet points)
   - Start each with a quantified statement: "X% of...", "Top 3... account for Y%", "Critical gap in..."
   - Flag any data quality red flags (high cardinality IDs, high missing%, sparse columns)
   - State what business question each column can answer

2. KPI RECOMMENDATIONS (3-5 metrics)
   - For each: column name, aggregation (sum/mean/count/max), business label, and WHY it matters
   - Focus on metrics that drive operational or financial decisions

3. CHART RECOMMENDATIONS (5-7 charts)
   - For each chart: type, x-column, y-column, business title, and 1-line analytical rationale
   - Prioritise: distribution analysis (bar/pie), trend decomposition (line if temporal),
     concentration analysis (treemap/funnel), outlier detection (box plot),
     cross-dimensional analysis (heatmap if multiple numerics)
   - Be specific about which columns to use and what insight the chart reveals

4. FILTER RECOMMENDATIONS (2-3 filters)
   - Identify the 2-3 categorical columns that segment the data most meaningfully for drill-down

5. STRATEGIC NARRATIVE (2-3 sentences)
   - What story does this data tell? What should leadership focus on first?

Return ONLY valid JSON - no markdown, no explanation text:

{{
  "executive_findings": ["finding1", "finding2", "finding3"],
  "data_quality_score": 0.0,
  "kpis": [
    {{"column": "col", "aggregation": "sum", "label": "Business Label", "rationale": "why it matters"}}
  ],
  "charts": [
    {{"type": "bar|pie|line|histogram|box|heatmap|funnel|treemap|scatter", "x": "col", "y": "col", "title": "Business Title", "rationale": "what insight this reveals"}}
  ],
  "filters": [
    {{"column": "col", "label": "Display Name", "rationale": "segmentation value"}}
  ],
  "narrative": "2-3 sentence strategic summary for leadership"
}}"""
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd D:/test && python -m pytest tests/test_prompts.py -v
```
Expected:
```
tests/test_prompts.py::test_prompt_contains_required_sections PASSED
tests/test_prompts.py::test_prompt_with_objective_prepends_goal PASSED
tests/test_prompts.py::test_prompt_objective_truncated_at_500_chars PASSED
tests/test_prompts.py::test_prompt_empty_objective_ignored PASSED
tests/test_prompts.py::test_prompt_whitespace_objective_ignored PASSED
5 passed
```

- [ ] **Step 5: Replace inline prompt in `dashboard.py` with `build_big_four_prompt()`**

Add import at the top of `dashboard.py` with the other llm imports:
```python
from llm.prompts import build_big_four_prompt
```

In `analyze_with_ai` (around line 670), find the large `prompt = f"""..."""` block (spanning ~50 lines). Replace the entire block with:

```python
        prompt = build_big_four_prompt(
            col_summary=col_summary,
            sample_str=sample_str,
            n_rows=len(current_df),
            n_cols=len(current_df.columns),
            n_kpis=len(kpi_selections or []),
            n_filters=len(filter_selections or []),
            objective='',  # wired in Task 5
        )
```

- [ ] **Step 6: Verify dashboard imports cleanly**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```

- [ ] **Step 7: Commit**

```bash
git add llm/prompts.py dashboard.py tests/
git commit -m "refactor: move Big Four prompt to llm/prompts.py as build_big_four_prompt()"
```

---

## Task 4: Add `store-objective` and Objective textarea

**Files:**
- Modify: `dashboard.py`
- Modify: `pages/page_config.py`

- [ ] **Step 1: Add `store-objective` to app layout in `dashboard.py`**

Find the stores block in `app.layout` (around line 461). Add after `store-ai-suggestions`:

```python
    # AI suggestions store
    dcc.Store(id='store-ai-suggestions', storage_type='memory', data=None),

    # Objective store — session-scoped analysis goal
    dcc.Store(id='store-objective', storage_type='memory', data=''),
```

- [ ] **Step 2: Add Objective textarea to AI Suggestions card in `pages/page_config.py`**

Find the LLM Analysis Section (around line 100). Replace the entire `html.Div([...])` block for that section with:

```python
        # LLM Analysis Section
        html.Div([
            html.H3("AI Suggestions", style={
                'fontSize': '18px', 'fontWeight': 'bold', 'color': TEXT, 'marginBottom': '12px'
            }),
            html.Div(
                "Get AI-powered recommendations for additional charts and analysis",
                style={'color': TEXT_LIGHT, 'fontSize': '12px', 'marginBottom': '16px'}
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

            html.Div([
                dbc.Button("Get AI Suggestions", id='btn-analyze-ai', color="success", size="sm"),
            ], style={'display': 'flex', 'justifyContent': 'flex-end'}),

            html.Div(id='ai-analysis-results', children=[], style={'marginTop': '15px'}),

        ], style={'background': CARD_BG, 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '30px',
                  'border': f'1px solid {BORDER}'}),
```

- [ ] **Step 3: Add sync callback for objective in `pages/page_config.py`**

Add at the bottom of `page_config.py`, after the `update_filter_items` callback:

```python
@callback(
    Output('store-objective', 'data'),
    Input('objective-input', 'value'),
    prevent_initial_call=True
)
def sync_objective(value):
    """Sync objective textarea to session store."""
    return (value or '').strip()
```

- [ ] **Step 4: Verify dashboard imports**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```

- [ ] **Step 5: Commit**

```bash
git add dashboard.py pages/page_config.py
git commit -m "feat: add Objective textarea to AI Suggestions card, sync to store-objective"
```

---

## Task 5: Wire `store-objective` into LLM callbacks

**Files:**
- Modify: `dashboard.py`

- [ ] **Step 1: Wire objective into `analyze_with_ai`**

Find the `@app.callback` decorator for `analyze_with_ai` (around line 622). Add `State('store-objective', 'data')` to the State list and update the function signature:

```python
@app.callback(
    Output('ai-analysis-results', 'children'),
    Output('store-ai-suggestions', 'data'),
    Output('kpi-column-selector', 'value'),
    Output('filter-column-selector', 'value'),
    Input('btn-analyze-ai', 'n_clicks'),
    [State('store-kpi-selections', 'data'),
     State('store-filter-selections', 'data'),
     State('store-objective', 'data')],
    running=[(Output('btn-analyze-ai', 'disabled'), True, False),
             (Output('btn-analyze-ai', 'children'), 'Analyzing...', 'Get AI Suggestions')],
    prevent_initial_call=True
)
def analyze_with_ai(n_clicks, kpi_selections, filter_selections, objective):
```

Update the `build_big_four_prompt` call (placed in Task 3) to pass objective:

```python
        prompt = build_big_four_prompt(
            col_summary=col_summary,
            sample_str=sample_str,
            n_rows=len(current_df),
            n_cols=len(current_df.columns),
            n_kpis=len(kpi_selections or []),
            n_filters=len(filter_selections or []),
            objective=objective or '',
        )
```

- [ ] **Step 2: Wire objective into `refresh_dashboard_analysis`**

Find the callback (around line 974). Add State and update the function:

```python
@app.callback(
    Output('store-llm-analysis', 'data'),
    Input('btn-refresh-analysis', 'n_clicks'),
    State('store-objective', 'data'),
    prevent_initial_call=True
)
def refresh_dashboard_analysis(n_clicks, objective):
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
```

- [ ] **Step 3: Wire objective into `sync_config_to_session`**

Find the callback (around line 595). Add objective input:

```python
@app.callback(
    Output('session-state', 'data'),
    [Input('store-kpi-selections', 'data'),
     Input('store-filter-selections', 'data'),
     Input('store-objective', 'data')],
    State('session-state', 'data'),
    prevent_initial_call=True
)
def sync_config_to_session(kpi_data, filter_data, objective_data, session_data):
    if session_data is None:
        session_data = {}
    if kpi_data:
        session_data['kpi_selections'] = kpi_data
    if filter_data:
        session_data['filter_selections'] = filter_data
    if objective_data:
        session_data['objective'] = objective_data
    return session_data
```

- [ ] **Step 4: Verify imports**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```

- [ ] **Step 5: Commit**

```bash
git add dashboard.py
git commit -m "feat: wire store-objective into analyze_with_ai, refresh, and session sync callbacks"
```

---

## Task 6: Performance fix — eliminate re-profiling in `display_page`

**Files:**
- Modify: `dashboard.py`

- [ ] **Step 1: Replace live profiling block in `display_page` with cached read**

Find the block inside `display_page` (around line 515) that calls `DataProfiler().profile()`. Replace:

```python
        # IMPORTANT: Reload data from cache to check for new uploads
        # This ensures uploaded files are used instead of cached store data
        current_df = load_data(DATA_PATH)
        from core.data_profiler import DataProfiler
        profiler = DataProfiler()
        current_profiles_obj = profiler.profile(current_df)

        # Convert profiles to dict format
        current_profiles = {
            name: {
                'dtype': p.dtype,
                'cardinality': p.cardinality,
                'missing_pct': p.missing_pct,
                'top_values': p.top_values if hasattr(p, 'top_values') else [],
                'is_temporal': p.is_temporal,
            }
            for name, p in current_profiles_obj.items()
        }
```

With:

```python
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
```

- [ ] **Step 2: Verify imports**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```

- [ ] **Step 3: Commit**

```bash
git add dashboard.py
git commit -m "perf: replace per-navigation DataProfiler re-profiling with load_cached_profiles()"
```

---

## Task 7: Performance fix — generalise startup coercion, simplify `get_cached_dataframe`

**Files:**
- Modify: `dashboard.py`

- [ ] **Step 1: Generalise startup coercion in `dashboard.py`**

Find the startup coercion block (around lines 116-134):

```python
# Apply preprocessing to convert string columns to numeric (e.g., Amount with commas)
preprocessor = DataPreprocessor()
df_processed = df.copy()

# Convert Amount column: remove commas and convert to numeric
if 'Amount' in df_processed.columns:
    try:
        df_processed['Amount'] = pd.to_numeric(
            df_processed['Amount'].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        )
        print("[OK] Amount column converted to numeric")
    except Exception as e:
        print(f"[WARN] Failed to convert Amount to numeric: {e}")
```

Replace with:

```python
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
```

Also remove the unused `preprocessor = DataPreprocessor()` line and the `DataPreprocessor` import if `DataPreprocessor` is used nowhere else. Check with:

```bash
cd D:/test && grep -n "DataPreprocessor" dashboard.py
```

If only appears in the startup block: remove the import line too.

- [ ] **Step 2: Simplify `get_cached_dataframe()` — remove redundant coercion loop**

Find `get_cached_dataframe()` (around line 137). The function ends with a `for col in df.columns:` coercion loop. Remove that entire loop. The function should simply load and return the frame:

```python
def get_cached_dataframe():
    """Load dataframe from cache -- user upload takes priority over default data."""
    df = None
    try:
        from core.cache_manager import CacheManager
        active_path = CacheManager.get_active_upload_path()
        if active_path and os.path.exists(active_path):
            with open(active_path, 'rb') as f:
                df = load(f)   # existing load call — do not change serialisation format
    except Exception as e:
        print(f"[WARN] Failed to load active upload in get_cached_dataframe: {e}")

    if df is None:
        try:
            with open(df_pickle_path, 'rb') as f:
                df = load(f)   # existing load call — do not change serialisation format
        except Exception as e:
            print(f"[ERROR] Failed to load cached dataframe: {e}")
            return None

    return df.copy()
    # Coercion loop removed — data is coerced once at startup and once on upload
```

Keep the existing `load` calls exactly as they are — only remove the coercion loop that follows.

- [ ] **Step 3: Run tests**

```bash
cd D:/test && python -m pytest tests/test_prompts.py -v
```
Expected: 5 passed.

- [ ] **Step 4: Verify startup**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```
Expected: `[OK] Startup coercion: N columns converted to numeric` in the logs.

- [ ] **Step 5: Commit**

```bash
git add dashboard.py
git commit -m "perf: generalise startup coercion to all columns, remove per-call coercion from get_cached_dataframe"
```

---

## Task 8: Security fixes — error handling

**Files:**
- Modify: `dashboard.py`

- [ ] **Step 1: Fix `display_page` error handler**

Find the `except Exception as e:` block at the end of `display_page` (around line 583):

```python
    except Exception as e:
        print(f"[ERROR] display_page callback error: {type(e).__name__}: {e}")
        return html.Div(
            [
                html.H3("Error in Dashboard"),
                html.P(f"{type(e).__name__}: {str(e)}"),
            ],
            style={'padding': '20px', 'backgroundColor': '#ffeeee', 'color': '#cc0000', 'fontFamily': 'monospace'}
        )
```

Replace with:

```python
    except Exception as e:
        import traceback
        print(f"[ERROR] display_page: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return html.Div([
            html.H3("Error loading page"),
            html.P("An error occurred. Check server logs for details."),
        ], style={'padding': '20px', 'backgroundColor': '#ffeeee', 'color': '#cc0000'})
```

- [ ] **Step 2: Fix `analyze_with_ai` error handler**

Find the `except Exception as e:` block at the end of `analyze_with_ai` (around line 959):

```python
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)[:150]}"
        print(f"[ERROR] AI analysis failed: {error_msg}\n{traceback.format_exc()}")
        err_el = html.Div([
            html.Strong("Analysis Error: "),
            html.Span(error_msg),
        ], style={'color': '#DC2626', 'padding': '12px', 'background': '#FEE2E2',
                  'borderRadius': '6px', 'fontSize': '13px'})
        return err_el, dash.no_update, dash.no_update, dash.no_update
```

Replace with:

```python
    except Exception as e:
        import traceback
        print(f"[ERROR] analyze_with_ai: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        err_el = html.Div([
            html.Strong("Analysis failed. "),
            html.Span("Check server logs for details."),
        ], style={'color': '#DC2626', 'padding': '12px', 'background': '#FEE2E2',
                  'borderRadius': '6px', 'fontSize': '13px'})
        return err_el, dash.no_update, dash.no_update, dash.no_update
```

- [ ] **Step 3: Run tests**

```bash
cd D:/test && python -m pytest tests/test_prompts.py -v
```
Expected: 5 passed.

- [ ] **Step 4: Verify imports**

```bash
cd D:/test && python -c "import dashboard; print('[OK]')"
```

- [ ] **Step 5: Commit**

```bash
git add dashboard.py
git commit -m "security: remove raw exception details from browser UI; log server-side only"
```

---

## Task 9: Write `docs/ONEX_AI_DASHBOARD_GUIDE.md`

**Files:**
- Create: `docs/ONEX_AI_DASHBOARD_GUIDE.md`

- [ ] **Step 1: Create the manual**

Create `docs/ONEX_AI_DASHBOARD_GUIDE.md` with the following content:

```markdown
# Onex AI Data Insight — Dashboard Guide

## 1. Overview

An intelligent, self-configuring dashboard that analyses data automatically and generates professional visualisations. Built as a 4-phase system.

### Architecture

| Phase | What it does |
|---|---|
| Phase 1 | Modular code — clean separation across `core/`, `intelligence/`, `llm/`, `callbacks/`, `pages/` |
| Phase 2 | Auto-analysis — `DataProfiler` detects column types; `LayoutBuilder` generates a working dashboard with no LLM |
| Phase 3 | LLM integration — column profiles + sample data sent to Ollama/LMStudio/Claude; JSON config returned |
| Phase 4 | Interactive UI — 4-page flow: Upload -> Review Data -> Configure Dashboard -> Dashboard |

### Tech Stack

| Component | Library | Purpose |
|---|---|---|
| Dashboard | `dash` + `plotly` | Interactive web UI and visualisations |
| Data | `pandas`, `numpy` | Loading, profiling, aggregation |
| LLM | Ollama, LMStudio, Claude API | AI-driven layout recommendations |
| HTTP | `requests` | LLM API communication |
| UI components | `dash-bootstrap-components` | Layout and styling |

---

## 2. Setup

### Install dependencies

```bash
cd D:\test
pip install -r requirements.txt
```

### Configure LLM provider

Edit `llm_config.json` at the project root.

**Ollama (primary):**
```json
{
  "provider": "ollama",
  "model_name": "qwen2.5-coder:14b",
  "base_url": "http://ollama.osourceglobal.com:11434",
  "include_sample_data": true
}
```

**LMStudio (local):**
```json
{
  "provider": "lmstudio",
  "model_name": "local-model",
  "base_url": "http://localhost:1234/v1",
  "include_sample_data": true
}
```

**Claude API:**
```json
{
  "provider": "claude",
  "api_key": "sk-ant-...",
  "include_sample_data": true
}
```

### Start the dashboard

```bash
python dashboard.py
```
Open `http://127.0.0.1:8050`.

---

## 3. Usage Flow

### Page 1 — Upload Data (`/upload`)
Upload a CSV, XLS, or XLSX file (max 50 MB). If no file is uploaded, the dashboard uses `data/data.csv`.

### Page 2 — Review Data (`/`)
Auto-detected column types are shown. Confirm or override:
- **Numeric** — used for KPIs and chart Y axes
- **Categorical** — used for filters and chart X axes
- **Temporal** — used for time-series charts

### Page 3 — Configure Dashboard (`/config`)

**KPI Metrics:** Select numeric columns, choose aggregation and label.

**Filters:** Select categorical columns for interactive filtering.

**Analysis Objective (optional):** Type a plain-English goal before clicking "Get AI Suggestions". Example:
> "Check monthly trend of expense and performance of the posters"

The LLM uses this to prioritise chart types, KPIs, and narrative.

**Get AI Suggestions:** Sends data to the configured LLM. Returns recommended KPIs, charts, filters, and an executive narrative. Pre-fills selectors automatically.

### Page 4 — Dashboard (`/dashboard`)
KPI cards, filter dropdowns, and charts. Filters update all charts simultaneously. **Refresh AI Analysis** re-runs the LLM with the current filter state and your objective.

---

## 4. LLM Providers

### Fallback chain
1. Ollama (from `llm_config.json`)
2. LMStudio
3. Claude API
4. Phase 2 auto-layout (always works — no LLM required)

### Privacy mode
Set `"include_sample_data": false` to send only column statistics, not row data.

---

## 5. Developing

### Add a chart type
1. Add the type string to `ChartConfig` docstring in `core/config.py`
2. Add a handler in `callbacks/chart_callbacks.py` (around line 55)

### Add an LLM provider
1. Create `llm/new_provider.py` extending `LLMProvider` from `llm/base_provider.py`
2. Register in `LLMFactory.create()` in `llm/config.py`
3. Set `"provider": "new_provider"` in `llm_config.json`

### Debug data profiling
```python
from core.data_profiler import DataProfiler
import pandas as pd
df = pd.read_csv('data/data.csv')
profiler = DataProfiler()
profiles = profiler.profile(df)
for name, p in profiles.items():
    print(f"{name}: {p.dtype}, cardinality={p.cardinality}, temporal={p.is_temporal}")
```

---

## 6. Data Reference

### Count aggregation (self-referencing columns)
```python
gdf = df.groupby(x_col).size().reset_index(name='count')
```
Used in `callbacks/chart_callbacks.py`. Using `.count().reset_index()` raises "column already exists".

### Temporal column detection
`DataProfiler` checks: dtype is string/object, date keywords in column name (`date`, `time`, `created`, `posted`, `parking`, `inward`, `invoice`), then attempts `pd.to_datetime()` — marks temporal if >50% parse.

### Numeric coercion
At startup, all non-numeric columns are tested. Columns where >50% of values convert (after stripping `,`, `₹`, `$`, `€`, `£`) are coerced to float. Runs once — all callbacks receive the already-coerced dataframe.

### Objective field
Stored in `store-objective` (session memory). Passed to `build_big_four_prompt(objective=...)` in `llm/prompts.py`. Truncated to 500 chars server-side. Resets on page refresh.

---

## 7. Troubleshooting

### LLM connection error
```
[WARN] LLM initialization failed - Server connection issue
```
- **Ollama:** `ollama serve`, then `ollama pull qwen2.5-coder:14b`. Update `base_url`.
- **LMStudio:** Launch app, download model, click "Start Server".
- **Skip LLM:** Delete `llm_config.json` — uses Phase 2 auto-layout.

### Module import error
```
ModuleNotFoundError: No module named 'core'
```
Run from the project root: `cd D:\test && python dashboard.py`

### Unicode encoding error (Windows)
```
UnicodeEncodeError: 'charmap' codec can't encode character
```
```bash
set PYTHONIOENCODING=utf-8
python dashboard.py
```

### Charts show no data after filter
Check the column type on the Data Review page. A column wrongly detected as numeric will not appear in the filter dropdown.
```

- [ ] **Step 2: Verify file exists**

```bash
ls D:/test/docs/ONEX_AI_DASHBOARD_GUIDE.md
```

- [ ] **Step 3: Commit**

```bash
git add docs/ONEX_AI_DASHBOARD_GUIDE.md
git commit -m "docs: add single consolidated manual docs/ONEX_AI_DASHBOARD_GUIDE.md"
```

---

## Task 10: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace "Recent Fixes" section with "Key Patterns"**

Find `## Recent Fixes (Current Session)` near the bottom of `CLAUDE.md`. Replace the entire section with:

```markdown
## Key Patterns

### Count Aggregation (Self-Referencing Columns)
When x_column == y_column, use `.size()` not `.count().reset_index()`:
```python
gdf = df.groupby(x_col).size().reset_index(name='count')
```

### Objective Field
User analysis goal is in `store-objective` (session memory store).
Always pass to `build_big_four_prompt(objective=...)` in `llm/prompts.py`.
Truncate server-side: `objective = (objective or '').strip()[:500]`

### Error Handling in Dash Callbacks
Never render raw `str(e)` or `type(e).__name__` in browser HTML.
Log server-side: `print(f"[ERROR] {type(e).__name__}: {e}\n{traceback.format_exc()}")`
Show generic UI message: `html.P("An error occurred. Check server logs for details.")`

### Temporal Detection
DataProfiler checks dtype, date keywords in column name, and pd.to_datetime() success rate (>50%).
Columns like "Inward Date" stored as strings are correctly detected as temporal.
```

- [ ] **Step 2: Add Objective to Phase 4 description**

Find the Phase 4 Features bullet list under `## 4-Phase Architecture`. Add:
```markdown
  - **Objective field**: Free-text goal on config page, synced to `store-objective`, injected into all LLM calls via `build_big_four_prompt()` in `llm/prompts.py`
```

- [ ] **Step 3: Update file structure tree**

Replace the existing file structure block with:

```
D:\test\
├── dashboard.py               # Main Dash app (all 4 phases integrated)
├── llm_config.json            # LLM provider configuration
├── data/
│   └── data.csv               # Invoice/enterprise data (61,688 rows x 33 cols)
├── docs/
│   └── ONEX_AI_DASHBOARD_GUIDE.md  # Single comprehensive manual
├── core/
│   ├── config.py              # Configuration dataclasses & theme colors
│   ├── components.py          # Reusable UI components
│   ├── data_profiler.py       # Column type detection
│   └── schemas.py             # Pydantic validation (optional)
├── intelligence/
│   ├── layout_builder.py      # Auto-layout generation
│   ├── llm_analyzer.py        # LLM integration
│   ├── insight_extractor.py   # Data quality insights
│   └── chart_recommender.py   # Chart type recommendations
├── llm/
│   ├── config.py              # LLMFactory & provider configuration
│   ├── base_provider.py       # Abstract provider class
│   ├── ollama_provider.py     # Ollama inference server
│   ├── lmstudio_provider.py   # LMStudio local inference
│   ├── claude_provider.py     # Claude API integration
│   └── prompts.py             # Prompt templates incl. build_big_four_prompt()
├── callbacks/
│   └── chart_callbacks.py     # Generic chart update callbacks
├── pages/
│   ├── page_upload.py         # Step 1: File upload
│   ├── page_data_review.py    # Step 2: Confirm column types
│   ├── page_config.py         # Step 3: Select KPIs, filters, Objective
│   └── page_dashboard.py      # Step 4: Interactive dashboard
├── tests/
│   └── test_prompts.py        # Tests for build_big_four_prompt()
└── outputs/                   # Generated charts & exports
```

- [ ] **Step 4: Update Notes for Claude section**

Replace the existing Notes section with:

```markdown
## Notes for Claude

- **Data Source**: Load from `D:\test\data\data.csv` (61,688 rows, 33 columns) or active upload via `get_cached_dataframe()`
- **Output Location**: Save charts/exports to `D:\test\outputs/`
- **Config Location**: Provider config in `D:\test\llm_config.json`
- **Manual**: All setup and usage docs in `docs/ONEX_AI_DASHBOARD_GUIDE.md`
- **Count Aggregation**: Use `.groupby().size().reset_index(name='count')` for self-references (see Key Patterns)
- **Objective Field**: Stored in `store-objective`; pass as `objective` to `build_big_four_prompt()` in `llm/prompts.py`
- **Error Handling**: Never put `str(e)` in Dash UI HTML — log server-side, show generic message in browser
- **LLM Analysis**: `include_sample_data: true` in `llm_config.json` for better recommendations
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — add Objective field, Key Patterns, remove stale Recent Fixes"
```

---

## Task 11: Update memory files

**Files:**
- Modify: `C:/Users/suraj.dubey/.claude/projects/D--test/memory/project_4phase_dashboard.md`
- Create: `C:/Users/suraj.dubey/.claude/projects/D--test/memory/feedback_error_handling.md`
- Modify: `C:/Users/suraj.dubey/.claude/projects/D--test/memory/project_dashboard_transformation.md`
- Modify: `C:/Users/suraj.dubey/.claude/projects/D--test/memory/MEMORY.md`

- [ ] **Step 1: Update `project_4phase_dashboard.md`**

Read the file, then append to the Phase 4 description:
```
- Objective field: dcc.Textarea on config page (/config), synced to store-objective (memory store), injected into all LLM calls via build_big_four_prompt() in llm/prompts.py; truncated to 500 chars server-side
```

Also update the file structure note: docs/ contains ONEX_AI_DASHBOARD_GUIDE.md; tests/ contains test_prompts.py; 14 stale files removed.

- [ ] **Step 2: Create `feedback_error_handling.md`**

```markdown
---
name: Error handling in Dash callbacks
description: Never expose raw exception details in Dash UI — log server-side, show generic browser message
type: feedback
---

Never render `str(e)` or `type(e).__name__` in HTML returned from Dash callbacks.

**Why:** Leaks internal file paths, column names, and stack fragments to the browser. Found in display_page and analyze_with_ai during security review.

**How to apply:** In all Dash except blocks:
- Log: `print(f"[ERROR] {type(e).__name__}: {e}\n{traceback.format_exc()}")`
- UI: `html.P("An error occurred. Check server logs for details.")`
```

- [ ] **Step 3: Update `project_dashboard_transformation.md`**

Add note: housekeeping complete — 14 stale files deleted, 7 docs consolidated into `docs/ONEX_AI_DASHBOARD_GUIDE.md`.

- [ ] **Step 4: Add entry to `MEMORY.md`**

Add to the index:
```
- [Error handling in Dash callbacks](feedback_error_handling.md) — Never expose raw str(e) in Dash UI; log server-side only
```

- [ ] **Step 5: Final test run**

```bash
cd D:/test && python -m pytest tests/test_prompts.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Final import check**

```bash
cd D:/test && python -c "import dashboard; print('[ALL OK]')"
```

- [ ] **Step 7: Commit memory files**

```bash
git add "C:/Users/suraj.dubey/.claude/projects/D--test/memory/"
git commit -m "docs: update memory — Objective field, error-handling rule, housekeeping complete"
```

---

## Self-Review

**Spec coverage:**
- Section 1 (Objective field) → Tasks 3, 4, 5
- Section 2 (Performance) → Tasks 6, 7
- Section 3 (Security) → Tasks 3 (input guard in `build_big_four_prompt`), 8 (error handlers)
- Section 4 (Code cleanup) → Tasks 1, 2
- Section 5 (Manual) → Task 9
- Section 6 (CLAUDE.md) → Task 10
- Section 7 (Memory) → Task 11

All sections covered. No gaps.

**Type consistency:** `build_big_four_prompt(col_summary, sample_str, n_rows, n_cols, n_kpis, n_filters, objective='')` used identically in Tasks 3, 4, 5. `store-objective` consistent across Tasks 4, 5, 10, 11. `objective-input` defined in Task 4 Step 2, synced in Task 4 Step 3.

**Placeholder scan:** No TBD, TODO, or "similar to above" patterns.
