# Dashboard Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auto date granularity, SQL WHERE filtering, database connectivity, a settings modal, and a correct data quality score to the existing 4-phase Dash dashboard.

**Architecture:** Five independent features share a single implementation cycle ordered by dependency: quality scorer and date granularity are pure additions; DB connector and query builder form the database path; the settings modal ties LLM + DB config together and the upload page gains a DB tab as the final integration step.

**Tech Stack:** Dash, Plotly, pandas, SQLAlchemy, dash-bootstrap-components, pytest

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `core/quality_scorer.py` | Weighted score from profiled column dicts |
| Create | `core/db_connector.py` | SQLAlchemy engine factory, table list, DataFrame fetch |
| Create | `core/query_builder.py` | Visual filter rows → parameterized SQL WHERE |
| Create | `components/__init__.py` | Package marker |
| Create | `components/settings_modal.py` | ⚙ modal with LLM + Database tabs |
| Create | `pages/page_db_source.py` | Database source tab UI (table picker + WHERE builder) |
| Create | `tests/test_quality_scorer.py` | Quality scorer unit tests |
| Create | `tests/test_db_connector.py` | DB connector unit tests (SQLite) |
| Create | `tests/test_query_builder.py` | Query builder unit tests |
| Modify | `core/data_profiler.py` | Add `temporal_granularity` to `ColumnProfile` |
| Modify | `core/cache_manager.py` | Persist `has_outliers`, `cardinality`, `temporal_granularity` in profiles JSON |
| Modify | `dashboard.py` | Persist same fields at startup; add ⚙ button + modal to layout |
| Modify | `callbacks/dashboard_callbacks.py` | Resample temporal x-axis before chart aggregation |
| Modify | `pages/page_dashboard.py` | Replace hardcoded quality score with `quality_scorer.compute()` |
| Modify | `pages/page_upload.py` | Add "Database" tab alongside File Upload tab |
| Modify | `llm_config.json` | Add `"database": {}` section |

---

## Task 1: Data Quality Scorer

**Files:**
- Create: `core/quality_scorer.py`
- Create: `tests/test_quality_scorer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_quality_scorer.py
import pytest
from core.quality_scorer import compute

def _p(missing_pct=0.0, has_outliers=False, cardinality=10):
    return {'missing_pct': missing_pct, 'has_outliers': has_outliers, 'cardinality': cardinality}

def test_perfect_data_scores_one():
    assert compute({'a': _p()}) == pytest.approx(1.0)

def test_missing_values_reduce_score():
    # 100% missing → penalty = 1.0 * 0.40 = 0.40 → score = 0.60
    score = compute({'a': _p(missing_pct=100.0)})
    assert score == pytest.approx(0.60, abs=0.01)

def test_constant_column_reduces_score():
    # cardinality=1 → penalty 0.05 → score = 0.95
    score = compute({'a': _p(cardinality=1)})
    assert score == pytest.approx(0.95, abs=0.01)

def test_outliers_reduce_score():
    # has_outliers → penalty 0.01 → score = 0.99
    score = compute({'a': _p(has_outliers=True)})
    assert score == pytest.approx(0.99, abs=0.01)

def test_combined_penalties_clamped_to_zero():
    # Worst possible column: 100% missing + outliers + constant
    p = _p(missing_pct=100.0, has_outliers=True, cardinality=1)
    score = compute({'a': p, 'b': p, 'c': p, 'd': p, 'e': p,
                     'f': p, 'g': p, 'h': p, 'i': p, 'j': p})
    assert score >= 0.0

def test_empty_profiles_returns_one():
    assert compute({}) == 1.0

def test_multiple_columns_averaged():
    # Two columns: one perfect, one 100% missing
    score = compute({'a': _p(), 'b': _p(missing_pct=100.0)})
    # per-col penalty = (0 + 0.40) / 2 = 0.20 → score = 0.80
    assert score == pytest.approx(0.80, abs=0.01)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_quality_scorer.py -v
```
Expected: `ModuleNotFoundError: No module named 'core.quality_scorer'`

- [ ] **Step 3: Create `core/quality_scorer.py`**

```python
from typing import Dict, Any

def compute(profiles: Dict[str, Any]) -> float:
    """Weighted data quality score from cached column profile dicts.

    profiles: dict of {col_name: {'missing_pct': float, 'has_outliers': bool, 'cardinality': int, ...}}
    Returns: float 0.0–1.0 (1.0 = perfect quality)
    """
    if not profiles:
        return 1.0
    penalties = 0.0
    for p in profiles.values():
        penalties += (p.get('missing_pct', 0.0) / 100.0) * 0.40
        if p.get('has_outliers', False):
            penalties += 0.01
        if p.get('cardinality', 10) == 1:
            penalties += 0.05
    per_column_penalty = penalties / len(profiles)
    return max(0.0, min(1.0, 1.0 - per_column_penalty))
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_quality_scorer.py -v
```
Expected: 7 PASSED

- [ ] **Step 5: Ensure `has_outliers` and `cardinality` are in startup profiles cache in `dashboard.py`**

Find this block around line 196–210 in `dashboard.py`:
```python
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
```
This already includes `has_outliers` and `cardinality`. ✓ No change needed here.

Also find the second `profiles_dict` block around line 364–372 (used for store data):
```python
profiles_dict = {}
for col_name, profile in profiles.items():
    profiles_dict[col_name] = {
        'dtype': profile.dtype,
        'cardinality': profile.cardinality,
        'missing_pct': profile.missing_pct,
        'top_values': profile.top_values,
        'is_temporal': profile.is_temporal,
    }
```
Replace with:
```python
profiles_dict = {}
for col_name, profile in profiles.items():
    profiles_dict[col_name] = {
        'dtype': profile.dtype,
        'cardinality': profile.cardinality,
        'missing_pct': profile.missing_pct,
        'top_values': profile.top_values,
        'is_temporal': profile.is_temporal,
        'has_outliers': getattr(profile, 'has_outliers', False),
    }
```

- [ ] **Step 6: Ensure `has_outliers` and `cardinality` are in `cache_manager.py` profiles JSON**

In `core/cache_manager.py`, find the profiles serialization (around line 47–57):
```python
profiles_dict = {
    name: {
        'dtype': p.dtype,
        'cardinality': p.cardinality,
        'missing_pct': p.missing_pct,
        'is_temporal': p.is_temporal,
    }
    for name, p in profiles.items()
}
```
Replace with:
```python
profiles_dict = {
    name: {
        'dtype': p.dtype,
        'cardinality': p.cardinality,
        'missing_pct': p.missing_pct,
        'is_temporal': p.is_temporal,
        'has_outliers': getattr(p, 'has_outliers', False),
    }
    for name, p in profiles.items()
}
```

- [ ] **Step 7: Wire `quality_scorer.compute()` into `pages/page_dashboard.py`**

Add import at top of `pages/page_dashboard.py`:
```python
from core.quality_scorer import compute as compute_quality_score
```

`generate_dashboard_page` receives `confirmed_dtypes` but not `profiles`. Add a `profiles` parameter:
```python
def generate_dashboard_page(
    df: pd.DataFrame,
    kpi_selections: list,
    filter_selections: list,
    confirmed_dtypes: dict,
    llm_analysis=None,
    profiles: dict = None,   # ← add this
) -> html.Div:
```

Compute score early in the function (after the `if not kpi_selections or not filter_selections:` guard):
```python
quality_score = compute_quality_score(profiles) if profiles else 0.85
```

Then replace every occurrence of `exec_summary.get('data_quality_score', 0.85)` — there are two:

**Line ~201** (health_score for executive_summary_card):
```python
health_score=quality_score,
status='healthy' if quality_score > 0.8 else 'caution',
```

**Line ~239** (footer label):
```python
html.P(
    f"Generated with AI-powered analysis | Data quality: {int(quality_score * 100)}%",
    style={'color': TEXT_LIGHT, 'fontSize': '12px', 'margin': '0', 'textAlign': 'center'}
),
```

- [ ] **Step 8: Update the caller of `generate_dashboard_page` in `dashboard.py` to pass `profiles`**

Search for `generate_dashboard_page(` in `dashboard.py`. Find the call and add `profiles=profiles_dict`:
```python
dashboard_page_layout = page_dashboard.generate_dashboard_page(
    df=df,
    kpi_selections=...,
    filter_selections=...,
    confirmed_dtypes=...,
    llm_analysis=...,
    profiles=profiles_dict,   # ← add this
)
```
Also find any other callers of `generate_dashboard_page` in callbacks and pass `profiles` from the store.

- [ ] **Step 9: Commit**

```bash
git add core/quality_scorer.py tests/test_quality_scorer.py \
        core/cache_manager.py pages/page_dashboard.py dashboard.py
git commit -m "feat: replace hardcoded quality score with weighted data-driven scorer"
```

---

## Task 2: Auto Date Granularity — Profiler

**Files:**
- Modify: `core/data_profiler.py`

- [ ] **Step 1: Add `temporal_granularity` to `ColumnProfile`**

In `core/data_profiler.py`, find the `ColumnProfile` dataclass and add one field after `is_temporal`:
```python
@dataclass
class ColumnProfile:
    name: str
    dtype: str
    cardinality: int
    missing_pct: float
    is_key_field: bool
    value_range: Optional[tuple]
    top_values: list
    is_temporal: bool
    temporal_granularity: Optional[str]   # ← add: 'hour'|'day'|'week'|'month'|None
    variance: Optional[float]
    skewness: Optional[float]
    has_outliers: bool
```

- [ ] **Step 2: Compute `temporal_granularity` inside `profile()`**

In the `profile()` method, after `is_temporal = self._is_temporal(series)`, add:
```python
temporal_granularity = self._get_temporal_granularity(series) if is_temporal else None
```

Update the `ColumnProfile(...)` construction to pass `temporal_granularity=temporal_granularity`.

- [ ] **Step 3: Add `_get_temporal_granularity()` method to `DataProfiler`**

```python
def _get_temporal_granularity(self, series: pd.Series) -> str:
    """Pick the best time granularity based on the column's date range."""
    try:
        parsed = pd.to_datetime(series, errors='coerce').dropna()
        if parsed.empty:
            return 'day'
        date_range_days = (parsed.max() - parsed.min()).days
        if date_range_days > 730:
            return 'month'
        if date_range_days > 60:
            return 'week'
        if date_range_days > 2:
            return 'day'
        return 'hour'
    except Exception:
        return 'day'
```

- [ ] **Step 4: Update profiles JSON serialization in `dashboard.py` to include `temporal_granularity`**

In the first `profiles_dict` block (around line 196, written to JSON file):
```python
profiles_dict = {
    name: {
        'dtype': profile.dtype,
        'cardinality': profile.cardinality,
        'missing_pct': profile.missing_pct,
        'value_range': profile.value_range if hasattr(profile, 'value_range') else None,
        'top_values': profile.top_values if hasattr(profile, 'top_values') else None,
        'is_temporal': profile.is_temporal,
        'temporal_granularity': getattr(profile, 'temporal_granularity', None),  # ← add
        'has_outliers': profile.has_outliers if hasattr(profile, 'has_outliers') else False,
    }
    for name, profile in profiles.items()
}
```

In the second `profiles_dict` block (around line 364, for the dcc.Store):
```python
profiles_dict[col_name] = {
    'dtype': profile.dtype,
    'cardinality': profile.cardinality,
    'missing_pct': profile.missing_pct,
    'top_values': profile.top_values,
    'is_temporal': profile.is_temporal,
    'temporal_granularity': getattr(profile, 'temporal_granularity', None),  # ← add
    'has_outliers': getattr(profile, 'has_outliers', False),
}
```

- [ ] **Step 5: Update `cache_manager.py` to persist `temporal_granularity`**

In `core/cache_manager.py` profiles serialization:
```python
profiles_dict = {
    name: {
        'dtype': p.dtype,
        'cardinality': p.cardinality,
        'missing_pct': p.missing_pct,
        'is_temporal': p.is_temporal,
        'temporal_granularity': getattr(p, 'temporal_granularity', None),  # ← add
        'has_outliers': getattr(p, 'has_outliers', False),
    }
    for name, p in profiles.items()
}
```

- [ ] **Step 6: Commit**

```bash
git add core/data_profiler.py core/cache_manager.py dashboard.py
git commit -m "feat: compute temporal_granularity on ColumnProfile; persist in profiles JSON"
```

---

## Task 3: Auto Date Granularity — Chart Resampling

**Files:**
- Modify: `callbacks/dashboard_callbacks.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_temporal_resampling.py
import pandas as pd
import pytest
from callbacks.dashboard_callbacks import _resample_temporal

def test_monthly_grouper_for_multi_year_range():
    dates = pd.date_range('2021-01-01', periods=36, freq='ME')
    df = pd.DataFrame({'order_date': dates, 'amount': range(36)})
    result = _resample_temporal(df, 'order_date', 'amount', 'sum', 'month')
    assert len(result) <= 36
    assert 'order_date' in result.columns
    assert 'amount' in result.columns

def test_daily_grouper():
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    df = pd.DataFrame({'order_date': dates, 'amount': range(20)})
    result = _resample_temporal(df, 'order_date', 'amount', 'sum', 'day')
    assert len(result) == 20

def test_non_temporal_returns_unchanged():
    df = pd.DataFrame({'category': ['A', 'B', 'C'], 'amount': [1, 2, 3]})
    result = _resample_temporal(df, 'category', 'amount', 'sum', None)
    assert len(result) == 3
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_temporal_resampling.py -v
```
Expected: `ImportError: cannot import name '_resample_temporal'`

- [ ] **Step 3: Add `_resample_temporal()` helper to `callbacks/dashboard_callbacks.py`**

Add this function near the top of `dashboard_callbacks.py` (after the existing helper functions like `_safe_nums`, `_safe_list`):

```python
_FREQ_MAP = {'month': 'ME', 'week': 'W', 'day': 'D', 'hour': 'h'}

def _resample_temporal(df: pd.DataFrame, x_col: str, y_col: str,
                       aggregation: str, granularity) -> pd.DataFrame:
    """Resample a DataFrame on a temporal x column at the given granularity.

    Returns a DataFrame with x_col and y_col (or 'count') columns.
    Falls back to returning df unchanged if parsing fails.
    """
    if not granularity or x_col not in df.columns:
        return df
    freq = _FREQ_MAP.get(granularity)
    if not freq:
        return df
    try:
        tmp = df.copy()
        tmp[x_col] = pd.to_datetime(tmp[x_col], errors='coerce')
        tmp = tmp.dropna(subset=[x_col])
        tmp = tmp.set_index(x_col).sort_index()

        agg_map = {'sum': 'sum', 'mean': 'mean', 'count': 'count', 'max': 'max', 'min': 'min'}
        agg_fn = agg_map.get(aggregation, 'sum')

        if y_col in tmp.columns:
            resampled = tmp[y_col].resample(freq).agg(agg_fn).dropna().reset_index()
        else:
            resampled = tmp.resample(freq).size().reset_index(name='count')
            y_col = 'count'

        return resampled
    except Exception as e:
        print(f"[WARN] _resample_temporal failed for {x_col}: {e}")
        return df
```

- [ ] **Step 4: Run test to confirm it passes**

```
pytest tests/test_temporal_resampling.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Use `_resample_temporal` in chart rendering inside `register_dashboard_callbacks`**

Inside `register_dashboard_callbacks`, find the chart update callback (search for `update_charts_on_filter` or similar). The callback receives `confirmed_dtypes` and `store-profiles` data from stores.

Add `State('store-profiles', 'data')` to the callback inputs if not already present. Then, before the groupby aggregation on each chart, check if the x-column is temporal:

```python
# Inside chart rendering, before groupby:
profiles_data = profiles_data or {}
x_profile = profiles_data.get(x_col, {})
is_temporal = x_profile.get('is_temporal', False)
granularity = x_profile.get('temporal_granularity', None)

if is_temporal and granularity:
    gdf = _resample_temporal(filtered_df, x_col, y_col, aggregation, granularity)
    # y_col may have changed to 'count' inside _resample_temporal — detect it:
    if 'count' in gdf.columns and y_col not in gdf.columns:
        y_col = 'count'
else:
    # existing groupby logic unchanged
    ...
```

Note: The exact location depends on where chart rendering happens in `register_dashboard_callbacks`. Search for `groupby` inside that function and wrap it with the temporal check above.

- [ ] **Step 6: Add `store-profiles` to `dashboard.py` layout if not already present**

Search for `dcc.Store(id='store-profiles'` in `dashboard.py`. If absent, add it to the stores section of the app layout:
```python
dcc.Store(id='store-profiles', data=profiles_dict),
```

- [ ] **Step 7: Commit**

```bash
git add callbacks/dashboard_callbacks.py dashboard.py tests/test_temporal_resampling.py
git commit -m "feat: auto date granularity — resample temporal charts by density-targeted freq"
```

---

## Task 4: Database Connector

**Files:**
- Create: `core/db_connector.py`
- Create: `tests/test_db_connector.py`

- [ ] **Step 1: Write failing tests (SQLite — no extra driver needed)**

```python
# tests/test_db_connector.py
import pandas as pd
import pytest
from core.db_connector import connect, test_connection, list_tables, fetch

@pytest.fixture
def sqlite_engine(tmp_path):
    engine = connect('sqlite', database=str(tmp_path / 'test.db'))
    # create a test table
    import sqlalchemy
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(
            "CREATE TABLE orders (id INTEGER, region TEXT, amount REAL)"
        ))
        conn.execute(sqlalchemy.text(
            "INSERT INTO orders VALUES (1, 'North', 100.0), (2, 'South', 200.0)"
        ))
        conn.commit()
    return engine

def test_connect_sqlite(tmp_path):
    engine = connect('sqlite', database=str(tmp_path / 'test2.db'))
    ok, msg = test_connection(engine)
    assert ok
    assert 'OK' in msg or 'ok' in msg.lower()

def test_list_tables(sqlite_engine):
    tables = list_tables(sqlite_engine)
    assert 'orders' in tables

def test_fetch_no_where(sqlite_engine):
    df = fetch(sqlite_engine, 'orders')
    assert len(df) == 2
    assert 'region' in df.columns

def test_fetch_with_where(sqlite_engine):
    df = fetch(sqlite_engine, 'orders', where_str='region = :p0', params={'p0': 'North'})
    assert len(df) == 1
    assert df.iloc[0]['region'] == 'North'

def test_fetch_limit(sqlite_engine):
    df = fetch(sqlite_engine, 'orders', limit=1)
    assert len(df) == 1

def test_connect_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported db_type"):
        connect('fakedb', database='x')
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_db_connector.py -v
```
Expected: `ModuleNotFoundError: No module named 'core.db_connector'`

- [ ] **Step 3: Create `core/db_connector.py`**

```python
"""SQLAlchemy-based database connector supporting multiple DB types."""
from typing import Optional, List, Tuple, Dict, Any
import pandas as pd
from sqlalchemy import create_engine, inspect, text, Engine


_URL_TEMPLATES: Dict[str, str] = {
    'postgresql': 'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}',
    'mysql':      'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
    'mssql':      'mssql+pyodbc://{user}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server',
    'sqlite':     'sqlite:///{database}',
    'oracle':     'oracle+cx_oracle://{user}:{password}@{host}:{port}/{database}',
}


def connect(
    db_type: str,
    host: str = 'localhost',
    port: int = None,
    database: str = '',
    user: str = '',
    password: str = '',
) -> Engine:
    """Create and return a SQLAlchemy Engine.

    Raises ValueError for unsupported db_type.
    Raises sqlalchemy.exc.* on connection errors (caller should catch).
    """
    db_type = db_type.lower()
    template = _URL_TEMPLATES.get(db_type)
    if not template:
        raise ValueError(f"Unsupported db_type '{db_type}'. Choose from: {list(_URL_TEMPLATES)}")

    default_ports = {'postgresql': 5432, 'mysql': 3306, 'mssql': 1433, 'oracle': 1521}
    resolved_port = port or default_ports.get(db_type, 0)

    url = template.format(
        host=host, port=resolved_port, database=database,
        user=user, password=password,
    )
    return create_engine(url, pool_pre_ping=True)


def test_connection(engine: Engine) -> Tuple[bool, str]:
    """Test engine connectivity. Returns (success, message)."""
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return True, "Connection OK"
    except Exception as e:
        return False, f"Connection failed: {type(e).__name__}: {str(e)[:200]}"


def list_tables(engine: Engine) -> List[str]:
    """Return sorted list of table and view names."""
    try:
        insp = inspect(engine)
        tables = insp.get_table_names()
        try:
            views = insp.get_view_names()
        except Exception:
            views = []
        return sorted(set(tables + views))
    except Exception as e:
        print(f"[WARN] list_tables failed: {e}")
        return []


def fetch(
    engine: Engine,
    table: str,
    where_str: str = '',
    params: Optional[Dict[str, Any]] = None,
    limit: int = 100_000,
) -> pd.DataFrame:
    """Fetch rows from table/view into a DataFrame.

    where_str: parameterized clause WITHOUT the 'WHERE' keyword,
               e.g. "region = :p0 AND amount > :p1"
    params: dict of bound values, e.g. {"p0": "North", "p1": 1000}
    """
    where_clause = f"WHERE {where_str}" if where_str.strip() else ''
    sql = f"SELECT * FROM {table} {where_clause} LIMIT {limit}"  # noqa: S608
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        print(f"[ERROR] fetch failed for {table}: {e}")
        return pd.DataFrame()
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_db_connector.py -v
```
Expected: 6 PASSED. If `sqlalchemy` not installed: `pip install sqlalchemy`.

- [ ] **Step 5: Commit**

```bash
git add core/db_connector.py tests/test_db_connector.py
git commit -m "feat: db_connector — SQLAlchemy engine factory supporting PostgreSQL, MySQL, SQL Server, SQLite, Oracle"
```

---

## Task 5: SQL WHERE Query Builder

**Files:**
- Create: `core/query_builder.py`
- Create: `tests/test_query_builder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_query_builder.py
import pytest
from core.query_builder import build, WhereCondition, VALID_OPERATORS

def test_single_eq_condition():
    conditions = [WhereCondition(column='region', operator='=', value='North')]
    where_str, params = build(conditions, allowed_columns=['region'])
    assert where_str == 'region = :p0'
    assert params == {'p0': 'North'}

def test_multiple_conditions_joined_with_and():
    conditions = [
        WhereCondition(column='region', operator='=', value='North'),
        WhereCondition(column='amount', operator='>', value='1000'),
    ]
    where_str, params = build(conditions, allowed_columns=['region', 'amount'])
    assert where_str == 'region = :p0 AND amount > :p1'
    assert params == {'p0': 'North', 'p1': '1000'}

def test_empty_conditions_returns_empty_string():
    where_str, params = build([], allowed_columns=['region'])
    assert where_str == ''
    assert params == {}

def test_invalid_column_raises():
    conditions = [WhereCondition(column='DROP TABLE x--', operator='=', value='x')]
    with pytest.raises(ValueError, match="Column .* not in allowed list"):
        build(conditions, allowed_columns=['region'])

def test_invalid_operator_raises():
    conditions = [WhereCondition(column='region', operator='EXEC', value='x')]
    with pytest.raises(ValueError, match="Operator .* not allowed"):
        build(conditions, allowed_columns=['region'])

def test_in_operator():
    conditions = [WhereCondition(column='region', operator='IN', value='North,South')]
    where_str, params = build(conditions, allowed_columns=['region'])
    assert 'IN' in where_str
    assert 'North' in str(params)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_query_builder.py -v
```
Expected: `ModuleNotFoundError: No module named 'core.query_builder'`

- [ ] **Step 3: Create `core/query_builder.py`**

```python
"""Build parameterized SQL WHERE clauses from visual filter selections."""
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

VALID_OPERATORS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'}


@dataclass
class WhereCondition:
    column: str
    operator: str
    value: str


def build(
    conditions: List[WhereCondition],
    allowed_columns: List[str],
) -> Tuple[str, Dict[str, Any]]:
    """Convert a list of WhereCondition into a parameterized SQL WHERE clause.

    Returns:
        where_str: clause string WITHOUT the 'WHERE' keyword, e.g. "col = :p0 AND col2 > :p1"
        params: dict of named bind parameters, e.g. {"p0": "North", "p1": 1000}

    Raises ValueError if a column is not in allowed_columns or operator is not in VALID_OPERATORS.
    """
    if not conditions:
        return '', {}

    allowed_set = set(allowed_columns)
    parts = []
    params: Dict[str, Any] = {}

    for i, cond in enumerate(conditions):
        if cond.column not in allowed_set:
            raise ValueError(f"Column '{cond.column}' not in allowed list: {sorted(allowed_set)}")
        op = cond.operator.upper()
        if op not in VALID_OPERATORS:
            raise ValueError(f"Operator '{cond.operator}' not allowed. Use: {sorted(VALID_OPERATORS)}")

        param_key = f'p{i}'
        if op == 'IN':
            # value is comma-separated string: "North,South"
            values = [v.strip() for v in cond.value.split(',')]
            placeholders = ', '.join(f':p{i}_{j}' for j in range(len(values)))
            parts.append(f'{cond.column} IN ({placeholders})')
            for j, v in enumerate(values):
                params[f'p{i}_{j}'] = v
        else:
            parts.append(f'{cond.column} {op} :{param_key}')
            params[param_key] = cond.value

    return ' AND '.join(parts), params
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_query_builder.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/query_builder.py tests/test_query_builder.py
git commit -m "feat: query_builder — safe parameterized SQL WHERE clause builder with column whitelist"
```

---

## Task 6: Database Source Page

**Files:**
- Create: `pages/page_db_source.py`

- [ ] **Step 1: Create `pages/page_db_source.py`**

This page renders inside the "Database" tab on the upload page. It returns a Dash layout and registers a set of callbacks when called from `dashboard.py`.

```python
"""Database source tab — connection form, table picker, WHERE builder, fetch trigger."""
import json
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback, ctx
import dash

from core.config import CARD_BG, TEXT, TEXT_LIGHT, BORDER, PRIMARY

DB_TYPES = ['postgresql', 'mysql', 'mssql', 'sqlite', 'oracle']
OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN']


def layout() -> html.Div:
    """Render the database connection + query form."""
    return html.Div([
        # Connection fields
        html.H5("Database Connection", style={'color': PRIMARY, 'marginBottom': '15px'}),
        dbc.Row([
            dbc.Col(dcc.Dropdown(
                id='db-type-select',
                options=[{'label': t.upper(), 'value': t} for t in DB_TYPES],
                placeholder='DB Type', clearable=False,
            ), width=2),
            dbc.Col(dbc.Input(id='db-host', placeholder='Host', value='localhost'), width=3),
            dbc.Col(dbc.Input(id='db-port', placeholder='Port', type='number'), width=1),
            dbc.Col(dbc.Input(id='db-name', placeholder='Database / File path'), width=3),
        ], className='mb-2'),
        dbc.Row([
            dbc.Col(dbc.Input(id='db-user', placeholder='Username'), width=3),
            dbc.Col(dbc.Input(id='db-password', placeholder='Password', type='password'), width=3),
            dbc.Col(dbc.Button('Connect', id='btn-db-connect', color='primary'), width=2),
            dbc.Col(html.Div(id='db-connect-status', style={'paddingTop': '8px', 'fontSize': '13px'}), width=4),
        ], className='mb-3'),

        # Table picker (shown after connect)
        html.Div(id='db-table-section', children=[
            html.H6("Select Table or View", style={'color': TEXT, 'marginTop': '10px'}),
            dcc.Dropdown(id='db-table-select', placeholder='Select table or view...'),
        ], style={'display': 'none'}),

        # WHERE builder (shown after table pick)
        html.Div(id='db-where-section', children=[
            html.H6("Filter Rows (optional)", style={'color': TEXT, 'marginTop': '15px'}),
            html.Div(id='db-where-rows', children=[]),
            dbc.Button('+ Add Condition', id='btn-add-where', outline=True,
                       color='secondary', size='sm', className='mt-2'),
        ], style={'display': 'none'}),

        # Fetch button
        html.Div(id='db-fetch-section', children=[
            dbc.Button('Fetch Data', id='btn-db-fetch', color='success',
                       className='mt-3', size='lg'),
            html.Div(id='db-fetch-status', style={'marginTop': '10px', 'fontSize': '13px'}),
        ], style={'display': 'none'}),

        # Hidden store for engine config (serializable connection params)
        dcc.Store(id='store-db-conn-params'),
        dcc.Store(id='store-db-columns'),
    ], style={'background': CARD_BG, 'padding': '20px', 'borderRadius': '8px',
              'border': f'1px solid {BORDER}'})


def register_callbacks(app, get_cached_df_fn, cache_manager_cls):
    """Register all DB source page callbacks."""

    @app.callback(
        Output('db-connect-status', 'children'),
        Output('db-table-section', 'style'),
        Output('db-table-select', 'options'),
        Output('store-db-conn-params', 'data'),
        Input('btn-db-connect', 'n_clicks'),
        State('db-type-select', 'value'),
        State('db-host', 'value'),
        State('db-port', 'value'),
        State('db-name', 'value'),
        State('db-user', 'value'),
        State('db-password', 'value'),
        prevent_initial_call=True,
    )
    def on_connect(n, db_type, host, port, database, user, password):
        if not db_type or not database:
            return 'Please fill in DB Type and Database fields.', {'display': 'none'}, [], None
        try:
            from core.db_connector import connect, test_connection, list_tables
            engine = connect(db_type, host or 'localhost', port, database, user or '', password or '')
            ok, msg = test_connection(engine)
            if not ok:
                return html.Span(msg, style={'color': '#DC2626'}), {'display': 'none'}, [], None
            tables = list_tables(engine)
            options = [{'label': t, 'value': t} for t in tables]
            conn_params = dict(db_type=db_type, host=host, port=port,
                               database=database, user=user, password=password)
            return (
                html.Span('Connected ✓', style={'color': '#16A34A'}),
                {'display': 'block'},
                options,
                conn_params,
            )
        except Exception as e:
            print(f"[ERROR] DB connect: {type(e).__name__}: {e}")
            return html.Span('Connection error. Check server logs.', style={'color': '#DC2626'}), {'display': 'none'}, [], None

    @app.callback(
        Output('db-where-section', 'style'),
        Output('db-fetch-section', 'style'),
        Output('store-db-columns', 'data'),
        Input('db-table-select', 'value'),
        State('store-db-conn-params', 'data'),
        prevent_initial_call=True,
    )
    def on_table_select(table, conn_params):
        if not table or not conn_params:
            raise dash.exceptions.PreventUpdate
        try:
            from core.db_connector import connect
            import sqlalchemy
            engine = connect(**{k: v for k, v in conn_params.items() if v is not None})
            with engine.connect() as conn:
                sample = conn.execute(sqlalchemy.text(f'SELECT * FROM {table} LIMIT 1'))
                columns = list(sample.keys())
            return {'display': 'block'}, {'display': 'block'}, columns
        except Exception as e:
            print(f"[ERROR] on_table_select: {e}")
            return {'display': 'none'}, {'display': 'none'}, []

    @app.callback(
        Output('db-where-rows', 'children'),
        Input('btn-add-where', 'n_clicks'),
        State('db-where-rows', 'children'),
        State('store-db-columns', 'data'),
        prevent_initial_call=True,
    )
    def add_where_row(n, existing_rows, columns):
        existing_rows = existing_rows or []
        i = len(existing_rows)
        row = dbc.Row([
            dbc.Col(dcc.Dropdown(
                id={'type': 'where-col', 'index': i},
                options=[{'label': c, 'value': c} for c in (columns or [])],
                placeholder='Column',
            ), width=4),
            dbc.Col(dcc.Dropdown(
                id={'type': 'where-op', 'index': i},
                options=[{'label': op, 'value': op} for op in OPERATORS],
                value='=', clearable=False,
            ), width=2),
            dbc.Col(dbc.Input(id={'type': 'where-val', 'index': i}, placeholder='Value'), width=4),
            dbc.Col(dbc.Button('✕', id={'type': 'where-remove', 'index': i},
                               color='danger', outline=True, size='sm'), width=1),
        ], className='mb-2')
        return existing_rows + [row]

    @app.callback(
        Output('db-fetch-status', 'children'),
        Output('upload-status', 'children'),  # reuse existing upload status div
        Input('btn-db-fetch', 'n_clicks'),
        State('db-table-select', 'value'),
        State('store-db-conn-params', 'data'),
        State({'type': 'where-col', 'index': ALL}, 'value'),
        State({'type': 'where-op', 'index': ALL}, 'value'),
        State({'type': 'where-val', 'index': ALL}, 'value'),
        prevent_initial_call=True,
    )
    def on_fetch(n, table, conn_params, cols, ops, vals):
        if not table or not conn_params:
            raise dash.exceptions.PreventUpdate
        try:
            from core.db_connector import connect, fetch
            from core.query_builder import build, WhereCondition

            engine = connect(**{k: v for k, v in conn_params.items() if v is not None})

            # Build WHERE clause from non-empty rows
            conditions = [
                WhereCondition(column=c, operator=o, value=v)
                for c, o, v in zip(cols, ops, vals)
                if c and o and v
            ]
            columns_for_whitelist = cols  # already from DB column list
            where_str, params = build(conditions, allowed_columns=[c for c in columns_for_whitelist if c])

            df = fetch(engine, table, where_str=where_str, params=params)
            if df.empty:
                return html.Span('No rows returned.', style={'color': '#D97706'}), dash.no_update

            # Save to cache using CacheManager
            upload_id, _ = cache_manager_cls.save_upload(df, filename=f'db:{table}')
            msg = html.Span(
                f'Loaded {len(df):,} rows × {len(df.columns)} cols from {table}',
                style={'color': '#16A34A'}
            )
            return msg, msg
        except ValueError as ve:
            return html.Span(f'Query error: {ve}', style={'color': '#DC2626'}), dash.no_update
        except Exception as e:
            print(f"[ERROR] on_fetch: {type(e).__name__}: {e}")
            return html.Span('Fetch failed. Check server logs.', style={'color': '#DC2626'}), dash.no_update
```

- [ ] **Step 2: Commit**

```bash
git add pages/page_db_source.py
git commit -m "feat: page_db_source — DB tab UI with connect, table picker, WHERE builder, fetch"
```

---

## Task 7: Settings Modal

**Files:**
- Create: `components/__init__.py`
- Create: `components/settings_modal.py`
- Modify: `llm_config.json`

- [ ] **Step 1: Create `components/__init__.py`**

```python
# empty package marker
```

- [ ] **Step 2: Create `components/settings_modal.py`**

```python
"""Settings modal — LLM configuration tab and Database configuration tab."""
import json
import os
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback
import dash

from core.config import TEXT, TEXT_LIGHT, BORDER, PRIMARY


LLM_PROVIDERS = ['ollama', 'lmstudio', 'claude']
DB_TYPES = ['postgresql', 'mysql', 'mssql', 'sqlite', 'oracle']
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'llm_config.json')


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(data: dict):
    existing = _load_config()
    existing.update(data)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(existing, f, indent=2)


def layout() -> dbc.Modal:
    """Return the settings modal component."""
    cfg = _load_config()
    db_cfg = cfg.get('database', {})

    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Settings")),
        dbc.ModalBody([
            dbc.Tabs([
                # ── LLM TAB ──────────────────────────────────────────
                dbc.Tab(label='LLM', tab_id='tab-llm', children=[
                    html.Div([
                        dbc.Label('Provider', style={'marginTop': '15px'}),
                        dcc.Dropdown(
                            id='settings-llm-provider',
                            options=[{'label': p.title(), 'value': p} for p in LLM_PROVIDERS],
                            value=cfg.get('provider', 'ollama'),
                            clearable=False,
                        ),
                        dbc.Label('Base URL', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-llm-url', value=cfg.get('base_url', ''),
                                  placeholder='http://localhost:11434'),
                        dbc.Label('Model Name', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-llm-model', value=cfg.get('model_name', ''),
                                  placeholder='qwen2.5-coder:14b'),
                        dbc.Label('API Key (Claude only)', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-llm-apikey', value=cfg.get('api_key', ''),
                                  type='password', placeholder='sk-ant-...'),
                        dbc.Checklist(
                            id='settings-llm-sample',
                            options=[{'label': 'Include sample data in LLM prompt', 'value': 'yes'}],
                            value=['yes'] if cfg.get('include_sample_data', True) else [],
                            style={'marginTop': '10px'},
                        ),
                    ])
                ]),
                # ── DATABASE TAB ──────────────────────────────────────
                dbc.Tab(label='Database', tab_id='tab-db', children=[
                    html.Div([
                        dbc.Label('DB Type', style={'marginTop': '15px'}),
                        dcc.Dropdown(
                            id='settings-db-type',
                            options=[{'label': t.upper(), 'value': t} for t in DB_TYPES],
                            value=db_cfg.get('db_type', ''),
                            placeholder='Select database type',
                        ),
                        dbc.Label('Host', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-db-host', value=db_cfg.get('host', 'localhost')),
                        dbc.Label('Port', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-db-port', value=db_cfg.get('port', ''),
                                  type='number', placeholder='5432'),
                        dbc.Label('Database Name', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-db-name', value=db_cfg.get('database', '')),
                        dbc.Label('Username', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-db-user', value=db_cfg.get('user', '')),
                        dbc.Label('Password', style={'marginTop': '10px'}),
                        dbc.Input(id='settings-db-password', type='password',
                                  value=db_cfg.get('password', '')),
                        dbc.Button('Test Connection', id='btn-settings-db-test', outline=True,
                                   color='info', size='sm', className='mt-3'),
                        html.Div(id='settings-db-test-result', style={'marginTop': '8px', 'fontSize': '13px'}),
                    ])
                ]),
            ], id='settings-tabs', active_tab='tab-llm'),
        ]),
        dbc.ModalFooter([
            html.Div(id='settings-save-status', style={'fontSize': '13px', 'marginRight': 'auto'}),
            dbc.Button('Save', id='btn-settings-save', color='primary'),
            dbc.Button('Close', id='btn-settings-close', color='secondary', outline=True,
                       className='ms-2'),
        ]),
    ], id='settings-modal', is_open=False, size='lg')


def register_callbacks(app):
    """Register open/close and save callbacks for the settings modal."""

    @app.callback(
        Output('settings-modal', 'is_open'),
        Input('btn-open-settings', 'n_clicks'),
        Input('btn-settings-close', 'n_clicks'),
        State('settings-modal', 'is_open'),
        prevent_initial_call=True,
    )
    def toggle_modal(open_clicks, close_clicks, is_open):
        return not is_open

    @app.callback(
        Output('settings-save-status', 'children'),
        Input('btn-settings-save', 'n_clicks'),
        State('settings-llm-provider', 'value'),
        State('settings-llm-url', 'value'),
        State('settings-llm-model', 'value'),
        State('settings-llm-apikey', 'value'),
        State('settings-llm-sample', 'value'),
        State('settings-db-type', 'value'),
        State('settings-db-host', 'value'),
        State('settings-db-port', 'value'),
        State('settings-db-name', 'value'),
        State('settings-db-user', 'value'),
        State('settings-db-password', 'value'),
        prevent_initial_call=True,
    )
    def save_settings(n, provider, url, model, apikey, sample,
                      db_type, db_host, db_port, db_name, db_user, db_password):
        try:
            data = {
                'provider': provider or 'ollama',
                'base_url': url or '',
                'model_name': model or '',
                'api_key': apikey or '',
                'include_sample_data': 'yes' in (sample or []),
                'database': {
                    'db_type': db_type or '',
                    'host': db_host or 'localhost',
                    'port': db_port,
                    'database': db_name or '',
                    'user': db_user or '',
                    'password': db_password or '',
                },
            }
            _save_config(data)
            return html.Span('Saved ✓', style={'color': '#16A34A'})
        except Exception as e:
            print(f"[ERROR] save_settings: {e}")
            return html.Span('Save failed. Check server logs.', style={'color': '#DC2626'})

    @app.callback(
        Output('settings-db-test-result', 'children'),
        Input('btn-settings-db-test', 'n_clicks'),
        State('settings-db-type', 'value'),
        State('settings-db-host', 'value'),
        State('settings-db-port', 'value'),
        State('settings-db-name', 'value'),
        State('settings-db-user', 'value'),
        State('settings-db-password', 'value'),
        prevent_initial_call=True,
    )
    def test_db(n, db_type, host, port, database, user, password):
        if not db_type or not database:
            return html.Span('Fill in DB Type and Database fields first.', style={'color': '#D97706'})
        try:
            from core.db_connector import connect, test_connection
            engine = connect(db_type, host or 'localhost', port, database, user or '', password or '')
            ok, msg = test_connection(engine)
            color = '#16A34A' if ok else '#DC2626'
            return html.Span(msg, style={'color': color})
        except Exception as e:
            print(f"[ERROR] settings test_db: {e}")
            return html.Span('Connection error. Check server logs.', style={'color': '#DC2626'})
```

- [ ] **Step 3: Add `"database": {}` section to `llm_config.json`**

Replace the contents of `llm_config.json` with:
```json
{
  "provider": "ollama",
  "model_name": "qwen2.5-coder:14b",
  "base_url": "http://ollama.osourceglobal.com:11434",
  "api_key": "",
  "include_sample_data": true,
  "database": {
    "db_type": "",
    "host": "localhost",
    "port": null,
    "database": "",
    "user": "",
    "password": ""
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add components/__init__.py components/settings_modal.py llm_config.json
git commit -m "feat: settings modal — LLM + database config tabs, save to llm_config.json"
```

---

## Task 8: Wire Everything into `dashboard.py` and `page_upload.py`

**Files:**
- Modify: `dashboard.py`
- Modify: `pages/page_upload.py`

- [ ] **Step 1: Add ⚙ button to navbar in `dashboard.py`**

In `make_navbar()`, find the return `html.Div([...])` and add a ⚙ button as the last item before the closing bracket of the nav row:

```python
# At the end of the nav items, before closing the outer html.Div:
dbc.Button(
    "⚙",
    id='btn-open-settings',
    color='link',
    style={'color': '#D4AF37', 'fontSize': '18px', 'padding': '4px 10px',
           'marginLeft': 'auto'},
),
```

- [ ] **Step 2: Import and register settings modal in `dashboard.py`**

Add import near the top of `dashboard.py` with the other page imports:
```python
from components import settings_modal
from pages import page_db_source
```

After `app = Dash(...)` and before `app.layout = ...`, add:
```python
settings_modal.register_callbacks(app)
page_db_source.register_callbacks(app, get_cached_dataframe, CacheManager)
```

Add the modal component to `app.layout`. Find where the main layout `html.Div` is returned and add the modal as a sibling to the main content:

```python
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    make_navbar('/'),          # existing
    settings_modal.layout(),   # ← add modal (hidden by default)
    html.Div(id='page-content', ...),   # existing
    # ... existing stores ...
])
```

- [ ] **Step 3: Add "Database" tab to `pages/page_upload.py`**

Replace the current `generate_upload_page()` return value's top section with a tabbed layout. Wrap the existing file upload content in `dbc.Tab` and add a second tab for the DB source:

```python
from pages import page_db_source as _db_src

def generate_upload_page():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Upload Your Data", className="mb-4", style={'color': PRIMARY}),
                html.P(
                    "Upload a file or connect directly to a database.",
                    style={'fontSize': '15px', 'color': TEXT}
                ),
            ])
        ], className="mt-4 mb-4"),

        dbc.Tabs([
            dbc.Tab(label='File Upload', tab_id='tab-file', children=[
                # ── EXISTING file upload content goes here (unchanged) ──
                # (Move all existing dbc.Row([...upload widget...]) blocks inside this tab)
            ]),
            dbc.Tab(label='Database', tab_id='tab-db', children=[
                html.Div(_db_src.layout(), className='mt-3'),
            ]),
        ], id='upload-source-tabs', active_tab='tab-file', className='mt-3'),
    ], fluid=True, style={'background': PRIMARY_BG, 'minHeight': '100vh', 'padding': '30px'})
```

Move all existing content (file upload widget + preview section) verbatim inside the `dbc.Tab(label='File Upload', ...)` children.

- [ ] **Step 4: Run the app and verify both paths work**

```bash
python dashboard.py
```
- Open `http://127.0.0.1:8050/upload`
- Confirm "File Upload" tab shows existing upload widget
- Confirm "Database" tab shows connection form
- Click ⚙ in navbar — settings modal should open with LLM and Database tabs
- Save settings — verify `llm_config.json` is updated on disk

- [ ] **Step 5: Commit**

```bash
git add dashboard.py pages/page_upload.py
git commit -m "feat: wire settings modal + DB source tab into app layout and navbar"
```

---

## Task 9: Run Full Test Suite

- [ ] **Step 1: Install new dependencies**

```bash
pip install sqlalchemy psycopg2-binary pymysql pyodbc
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v
```
Expected: All existing tests pass + new tests from Tasks 1, 4, 5, 3 pass.

If `pyodbc` is not available on the CI machine, mark the mssql test:
```python
@pytest.mark.skipif(not _pyodbc_available(), reason='pyodbc not installed')
```

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "chore: install sqlalchemy + DB drivers; all tests passing"
```

---

## Dependency Order Summary

```
Task 1  (quality scorer)       — standalone
Task 2  (profiler granularity) — standalone
Task 3  (chart resampling)     — depends on Task 2
Task 4  (db_connector)         — standalone
Task 5  (query_builder)        — standalone
Task 6  (page_db_source)       — depends on Task 4 + 5
Task 7  (settings_modal)       — depends on Task 4
Task 8  (wiring)               — depends on Tasks 6 + 7
Task 9  (tests)                — depends on all
Task 10 (background LLM)       — standalone, modifies dashboard.py
Task 11 (gunicorn)             — standalone
Task 12 (upload size cap)      — standalone, modifies dashboard.py
Task 13 (upload preview)       — standalone, modifies page_upload.py
Task 14 (save/load configs)    — standalone
```

---

## Task 10: Background LLM Thread + Live Dashboard Update

**Files:**
- Modify: `dashboard.py`
- Modify: `pages/page_dashboard.py`

**Context:** Currently Phase 3 LLM analysis blocks `python dashboard.py` startup for 1–5 minutes. This task moves it to a background thread so the app starts instantly and the dashboard refreshes silently when LLM completes.

- [ ] **Step 1: Add thread-safe LLM result store to `dashboard.py`**

After the `profiles_dict` / `config_dict` pre-init block (around line 376), add:

```python
import threading

# Thread-safe store for async LLM result
_llm_result_lock = threading.Lock()
_llm_result = {'config': None, 'done': False, 'exec_summary': None}
```

- [ ] **Step 2: Move Phase 3 LLM call into a background thread**

Find the Phase 3 block (the `try: ... llm_config_result = llm_analyzer.analyze(...)` block, around lines 277–341) and replace it with:

```python
# Phase 3 runs in background — app starts immediately
def _run_llm_analysis():
    try:
        result = llm_analyzer.analyze(df, profiles, user_context)
        with _llm_result_lock:
            _llm_result['config'] = result
            _llm_result['done'] = True
        print("[OK] Background LLM analysis complete")
    except Exception as e:
        print(f"[WARN] Background LLM analysis failed: {type(e).__name__}: {e}")
        with _llm_result_lock:
            _llm_result['done'] = True

if llm_analyzer:
    threading.Thread(target=_run_llm_analysis, daemon=True).start()
    print("[OK] LLM analysis started in background — app ready immediately")
```

- [ ] **Step 3: Add `dcc.Interval` + status div to `pages/page_dashboard.py`**

In `generate_dashboard_page()`, add these two components to the layout (near the top, after the executive summary card):

```python
# Polling interval — fires every 3s, stops after LLM result arrives
dcc.Interval(id='llm-poll-interval', interval=3000, n_intervals=0, disabled=False),
html.Div(
    id='llm-loading-banner',
    children=html.Div([
        dbc.Spinner(size='sm', color='warning', type='border'),
        html.Span(" AI analysis running in background…",
                  style={'color': '#D97706', 'fontSize': '13px', 'marginLeft': '8px'}),
    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '8px 16px',
              'background': '#FFF7ED', 'borderRadius': '6px', 'marginBottom': '12px',
              'border': '1px solid #FED7AA'}),
    style={'display': 'block'},
),
```

- [ ] **Step 4: Add polling callback to `callbacks/dashboard_callbacks.py`**

Inside `register_dashboard_callbacks`, add:

```python
@app.callback(
    Output('executive-summary-container', 'children'),
    Output('llm-loading-banner', 'style'),
    Output('llm-poll-interval', 'disabled'),
    Input('llm-poll-interval', 'n_intervals'),
    prevent_initial_call=True,
)
def poll_llm_result(n):
    import dashboard as _dash_module
    with _dash_module._llm_result_lock:
        done = _dash_module._llm_result.get('done', False)
        llm_config = _dash_module._llm_result.get('config')

    if not done:
        raise dash.exceptions.PreventUpdate

    # LLM done — hide banner, stop interval
    hidden = {'display': 'none'}
    if llm_config and hasattr(llm_config, 'exec_summary'):
        from core.components import executive_summary_card
        exec_summary = llm_config.exec_summary or {}
        from core.quality_scorer import compute as compute_quality_score
        profiles = _dash_module.load_cached_profiles()
        quality_score = compute_quality_score(profiles) if profiles else 0.85
        updated_card = executive_summary_card(
            title="Executive Summary",
            findings=exec_summary.get('key_findings', []),
            health_score=quality_score,
            status='healthy' if quality_score > 0.8 else 'caution',
            narrative=exec_summary.get('narrative', ''),
            risk_flags=exec_summary.get('risk_flags', []),
            priority_action=exec_summary.get('priority_action', ''),
        )
        return updated_card, hidden, True
    return dash.no_update, hidden, True
```

- [ ] **Step 5: Start app and verify instant startup**

```bash
python dashboard.py
```
Expected: App is available at `http://127.0.0.1:8050` within 5 seconds. Loading banner appears on dashboard page. Banner disappears when LLM completes (watch terminal for `[OK] Background LLM analysis complete`).

- [ ] **Step 6: Commit**

```bash
git add dashboard.py pages/page_dashboard.py callbacks/dashboard_callbacks.py
git commit -m "feat: move Phase 3 LLM to background thread; dashboard polls and updates live"
```

---

## Task 11: Gunicorn Multi-Worker Support

**Files:**
- Modify: `dashboard.py`
- Create: `gunicorn.conf.py`

**Context:** The default Dash dev server is single-threaded. One slow LLM call blocks all users. Gunicorn with multiple workers fixes this for production use.

- [ ] **Step 1: Expose Flask server object in `dashboard.py`**

Near the bottom of `dashboard.py`, find `app.run(` and ensure `server` is exposed before it:

```python
server = app.server  # expose for gunicorn: gunicorn dashboard:server
```

Also add upload size cap at the same time (Task 12 prereq):
```python
server.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB
```

- [ ] **Step 2: Create `gunicorn.conf.py`**

```python
# gunicorn.conf.py — production server configuration
bind = '0.0.0.0:8050'
workers = 4
threads = 2
timeout = 120          # allow slow LLM calls
worker_class = 'sync'
accesslog = '-'
errorlog = '-'
loglevel = 'info'
```

- [ ] **Step 3: Install gunicorn**

```bash
pip install gunicorn
```

- [ ] **Step 4: Verify gunicorn starts (Linux/Mac only — Windows uses waitress)**

On Linux/Mac:
```bash
gunicorn dashboard:server -c gunicorn.conf.py
```

On Windows (gunicorn doesn't support Windows):
```bash
pip install waitress
waitress-serve --port=8050 dashboard:server
```

Expected: App available at `http://0.0.0.0:8050`, 4 worker processes logged.

- [ ] **Step 5: Guard the dev-server block so `python dashboard.py` still works**

Find `app.run(` at the bottom of `dashboard.py` and wrap it:

```python
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
```

- [ ] **Step 6: Commit**

```bash
git add dashboard.py gunicorn.conf.py
git commit -m "feat: expose gunicorn-compatible server object; add gunicorn.conf.py for production"
```

---

## Task 12: Upload Size Cap + 413 Error Handling

**Files:**
- Modify: `dashboard.py`
- Modify: `pages/page_upload.py` (callback area)

**Context:** Without a size cap, a 500 MB upload silently OOMs the server. Flask's `MAX_CONTENT_LENGTH` enforces the limit at the HTTP layer and returns a 413 before Dash processes the file.

- [ ] **Step 1: Set `MAX_CONTENT_LENGTH` in `dashboard.py`**

If not already done in Task 11, add after `server = app.server`:

```python
server.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB hard limit
```

- [ ] **Step 2: Handle 413 in the upload callback**

In `dashboard.py` (or wherever the `upload-data` callback is registered), find the callback that handles file uploads (Input `'upload-data'`, `'contents'`). Add a 413 error handler on the Flask server:

```python
from flask import request, jsonify

@server.errorhandler(413)
def upload_too_large(e):
    return jsonify({'error': 'File too large. Maximum upload size is 50 MB.'}), 413
```

- [ ] **Step 3: Update the upload status message to show the limit**

In `pages/page_upload.py`, find:
```python
children=html.Div("Maximum file size: 50 MB", style={'color': '#9CA3AF', 'fontSize': '12px'})
```
This already exists — confirm it's accurate. If the text says something else, update it to match the 50 MB limit set above.

- [ ] **Step 4: Commit**

```bash
git add dashboard.py
git commit -m "feat: cap upload size at 50 MB via Flask MAX_CONTENT_LENGTH; handle 413"
```

---

## Task 13: Data Preview After Upload

**Files:**
- Modify: `pages/page_upload.py`
- Modify: `dashboard.py` (or wherever the upload callback lives)

**Context:** Users can't confirm the right file loaded without seeing the data. Show first 5 rows in a table immediately after upload completes.

- [ ] **Step 1: Add `dash_table` import to `pages/page_upload.py`**

```python
from dash import dash_table
```

- [ ] **Step 2: Add preview container to the upload page layout**

In `generate_upload_page()`, after the `upload-status` div, add:

```python
html.Div(id='upload-preview-container', children=[], style={'marginTop': '20px'}),
```

- [ ] **Step 3: Update upload callback to render preview**

Find the callback that processes the uploaded file (in `dashboard.py`, triggers on `Input('upload-data', 'contents')`). After successfully loading the DataFrame and saving to cache, add:

```python
# Build 5-row preview
preview_df = df.head(5)
preview_table = dash_table.DataTable(
    data=preview_df.to_dict('records'),
    columns=[{'name': c, 'id': c} for c in preview_df.columns],
    style_table={'overflowX': 'auto', 'maxHeight': '300px'},
    style_header={
        'backgroundColor': '#1A365D',
        'color': '#D4AF37',
        'fontWeight': 'bold',
        'fontSize': '12px',
    },
    style_cell={
        'fontSize': '12px',
        'padding': '6px 12px',
        'textAlign': 'left',
        'maxWidth': '200px',
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
    },
    style_data_conditional=[
        {'if': {'row_index': 'odd'}, 'backgroundColor': '#F9FAFB'}
    ],
    page_action='none',
    tooltip_delay=0,
    tooltip_duration=None,
)

preview_section = html.Div([
    html.H6(
        f"Preview: {len(df):,} rows × {len(df.columns)} columns",
        style={'color': '#1A365D', 'marginBottom': '10px', 'fontWeight': 'bold'}
    ),
    preview_table,
], style={
    'background': '#FFFFFF',
    'padding': '16px',
    'borderRadius': '8px',
    'border': '1px solid #E2E8F0',
    'marginTop': '16px',
})
```

Return `preview_section` as the value for `Output('upload-preview-container', 'children')`.

- [ ] **Step 4: Commit**

```bash
git add pages/page_upload.py dashboard.py
git commit -m "feat: show 5-row data preview immediately after upload"
```

---

## Task 14: Persist and Reload Dashboard Configs

**Files:**
- Create: `core/config_store.py`
- Modify: `pages/page_config.py`
- Create: `tests/test_config_store.py`

**Context:** Users reconfigure KPIs and filters every session. This task adds Save/Load buttons to the config page so layouts can be named and reused.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config_store.py
import pytest
import json
from pathlib import Path
from core.config_store import save_config, load_config, list_configs, delete_config

@pytest.fixture
def store_dir(tmp_path):
    return str(tmp_path / 'configs')

def test_save_and_load_roundtrip(store_dir):
    payload = {
        'kpi_selections': [{'column': 'amount', 'aggregation': 'sum', 'label': 'Total'}],
        'filter_selections': [{'column': 'region', 'filter_type': 'dropdown', 'label': 'Region'}],
    }
    save_config('my-layout', payload, store_dir=store_dir)
    loaded = load_config('my-layout', store_dir=store_dir)
    assert loaded == payload

def test_list_configs_returns_saved_names(store_dir):
    save_config('layout-a', {}, store_dir=store_dir)
    save_config('layout-b', {}, store_dir=store_dir)
    names = list_configs(store_dir=store_dir)
    assert 'layout-a' in names
    assert 'layout-b' in names

def test_load_missing_returns_none(store_dir):
    assert load_config('does-not-exist', store_dir=store_dir) is None

def test_delete_config(store_dir):
    save_config('temp', {}, store_dir=store_dir)
    delete_config('temp', store_dir=store_dir)
    assert load_config('temp', store_dir=store_dir) is None

def test_save_sanitizes_name(store_dir):
    # Names with path traversal characters should be sanitized
    save_config('../evil', {'x': 1}, store_dir=store_dir)
    names = list_configs(store_dir=store_dir)
    assert '../evil' not in names
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_config_store.py -v
```
Expected: `ModuleNotFoundError: No module named 'core.config_store'`

- [ ] **Step 3: Create `core/config_store.py`**

```python
"""Persist and retrieve named dashboard configurations (KPI + filter selections)."""
import json
import os
import re
from typing import Any, Dict, List, Optional

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache', 'saved_configs')


def _safe_name(name: str) -> str:
    """Strip path traversal characters; keep only alphanumeric, dash, underscore."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)[:80]


def _path(name: str, store_dir: str) -> str:
    return os.path.join(store_dir, f'{_safe_name(name)}.json')


def save_config(name: str, payload: Dict[str, Any], store_dir: str = _DEFAULT_DIR) -> None:
    """Save a named dashboard config to disk."""
    os.makedirs(store_dir, exist_ok=True)
    with open(_path(name, store_dir), 'w') as f:
        json.dump(payload, f, indent=2)


def load_config(name: str, store_dir: str = _DEFAULT_DIR) -> Optional[Dict[str, Any]]:
    """Load a named config. Returns None if not found."""
    p = _path(name, store_dir)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def list_configs(store_dir: str = _DEFAULT_DIR) -> List[str]:
    """Return sorted list of saved config names (without .json extension)."""
    if not os.path.exists(store_dir):
        return []
    return sorted(
        f[:-5] for f in os.listdir(store_dir) if f.endswith('.json')
    )


def delete_config(name: str, store_dir: str = _DEFAULT_DIR) -> None:
    """Delete a saved config. Silent if not found."""
    p = _path(name, store_dir)
    if os.path.exists(p):
        os.remove(p)
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_config_store.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Add Save / Load UI to `pages/page_config.py`**

At the top of `generate_config_page()`, before the KPI section, add a saved-configs row:

```python
from core.config_store import list_configs, load_config

saved_names = list_configs()

saved_configs_section = html.Div([
    html.H3("Saved Layouts", style={'fontSize': '16px', 'fontWeight': 'bold',
                                     'color': TEXT, 'marginBottom': '10px'}),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='saved-config-select',
                options=[{'label': n, 'value': n} for n in saved_names],
                placeholder='Select a saved layout to load…',
            ), width=6,
        ),
        dbc.Col(dbc.Button('Load', id='btn-load-config', color='secondary',
                           outline=True, size='sm'), width=2),
        dbc.Col(
            dbc.InputGroup([
                dbc.Input(id='save-config-name', placeholder='Layout name…', size='sm'),
                dbc.Button('Save Current', id='btn-save-config', color='info',
                           outline=True, size='sm'),
            ]), width=4,
        ),
    ], align='center'),
    html.Div(id='config-save-load-status', style={'fontSize': '12px', 'marginTop': '6px'}),
], style={'background': CARD_BG, 'padding': '15px', 'borderRadius': '8px',
          'marginBottom': '20px', 'border': f'1px solid {BORDER}'})
```

Include `saved_configs_section` as the first child in the returned layout.

- [ ] **Step 6: Register Save/Load callbacks in `dashboard.py`**

After registering other callbacks, add:

```python
@app.callback(
    Output('config-save-load-status', 'children'),
    Output('saved-config-select', 'options'),
    Input('btn-save-config', 'n_clicks'),
    State('save-config-name', 'value'),
    State('store-kpi-selections', 'data'),
    State('store-filter-selections', 'data'),
    prevent_initial_call=True,
)
def save_dashboard_config(n, name, kpi_data, filter_data):
    if not name or not name.strip():
        return html.Span('Enter a layout name first.', style={'color': '#D97706'}), dash.no_update
    from core.config_store import save_config, list_configs
    payload = {'kpi_selections': kpi_data or [], 'filter_selections': filter_data or []}
    save_config(name.strip(), payload)
    updated_options = [{'label': n, 'value': n} for n in list_configs()]
    return html.Span(f'Saved "{name}" ✓', style={'color': '#16A34A'}), updated_options


@app.callback(
    Output('store-kpi-selections', 'data'),
    Output('store-filter-selections', 'data'),
    Output('config-save-load-status', 'children', allow_duplicate=True),
    Input('btn-load-config', 'n_clicks'),
    State('saved-config-select', 'value'),
    prevent_initial_call=True,
)
def load_dashboard_config(n, name):
    if not name:
        return dash.no_update, dash.no_update, html.Span('Select a layout first.', style={'color': '#D97706'})
    from core.config_store import load_config
    payload = load_config(name)
    if not payload:
        return dash.no_update, dash.no_update, html.Span('Layout not found.', style={'color': '#DC2626'})
    return (
        payload.get('kpi_selections', []),
        payload.get('filter_selections', []),
        html.Span(f'Loaded "{name}" ✓', style={'color': '#16A34A'}),
    )
```

- [ ] **Step 7: Commit**

```bash
git add core/config_store.py tests/test_config_store.py pages/page_config.py dashboard.py
git commit -m "feat: save and load named dashboard configs (KPI + filter selections)"
```
