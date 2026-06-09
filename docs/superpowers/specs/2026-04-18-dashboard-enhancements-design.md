# Dashboard Enhancements — Design Spec
**Date:** 2026-04-18  
**Scope:** 5 features — date granularity, SQL WHERE filter, DB connectivity, settings modal, data quality fix

---

## 1. Overview

Five independent enhancements to the existing 4-phase Dash dashboard system. All changes feed into the existing Phase 2→3→4 pipeline — the profiling, LLM, and chart layers are unchanged except where noted. File upload and database connection are parallel, equally supported data source paths.

---

## 2. Architecture

### New Files

| File | Purpose |
|---|---|
| `core/db_connector.py` | SQLAlchemy connection manager: connect, test, list tables, fetch DataFrame |
| `core/query_builder.py` | Converts visual filter rows → parameterized SQL WHERE clause |
| `core/quality_scorer.py` | Weighted data quality score from `ColumnProfile` objects |
| `pages/page_db_source.py` | Database source tab UI (table picker + WHERE builder) |
| `components/settings_modal.py` | ⚙ modal with LLM tab and Database tab |

### Modified Files

| File | Change |
|---|---|
| `core/data_profiler.py` | Add `temporal_granularity` field to `ColumnProfile`; compute in `_is_temporal()` |
| `callbacks/chart_callbacks.py` | Resample temporal x-axis using `temporal_granularity` before plotting |
| `pages/page_upload.py` | Add "Database" tab alongside existing "File Upload" tab |
| `dashboard.py` | Register settings modal + ⚙ navbar button; load DB config from `llm_config.json` |
| `pages/page_dashboard.py` | Replace hardcoded `data_quality_score` fallback with `quality_scorer.compute()` |
| `llm_config.json` | Add `"database"` section for persisted DB connection settings |

### Data Flow

```
[File Upload tab]  ──────────────────────────────────────────┐
                                                              ▼
[Database tab] → db_connector.fetch(table, where, params) → DataFrame
                                                              ▼
                        Phase 2: DataProfiler (unchanged)
                                                              ▼
                        Phase 3: LLM Analyzer (unchanged)
                                                              ▼
                        Phase 4: Dashboard (unchanged except quality score)
```

---

## 3. Feature Details

### F1 — Auto Date Granularity

**Where:** `core/data_profiler.py` + `callbacks/chart_callbacks.py`

**Logic:** After `_is_temporal()` confirms a column is temporal, compute `temporal_granularity` on the `ColumnProfile` using the date range of the column:

```
date_range = max_date - min_date
> 730 days  → 'month'
> 60 days   → 'week'
> 2 days    → 'day'
≤ 2 days    → 'hour'
```

`ColumnProfile` gains one new field: `temporal_granularity: Optional[str]` (None for non-temporal columns).

In `chart_callbacks.py`, when the x-axis column profile is temporal, resample the DataFrame using `pd.Grouper(freq=...)` before aggregating:

| granularity | `pd.Grouper freq` |
|---|---|
| month | `'ME'` |
| week | `'W'` |
| day | `'D'` |
| hour | `'h'` |

No user interaction required. Fully automatic.

---

### F2 — SQL WHERE Builder

**Where:** `core/query_builder.py` + `pages/page_db_source.py`

**UI (DB tab only):** After the user picks a table/view, a filter builder appears:

- Each row: `[Column dropdown] [Operator: =, ≠, >, <, >=, <=, IN, LIKE] [Value input]`
- "+ Add Condition" button adds rows; "✕" removes rows
- Conditions joined with AND logic
- "Fetch Data" button executes the query

**`query_builder.build(conditions) → (where_str, params)`**

Returns a parameterized WHERE clause string and a list of bound values. Values are never string-interpolated into SQL — passed as parameters to SQLAlchemy `engine.execute(text(sql), params)`.

Example output: `"WHERE region = :p0 AND amount > :p1"`, `{"p0": "North", "p1": 1000}`

**Injection safety:** Column names are validated against the fetched column list (whitelist). Operators are an enum. Only values come from user input and are always parameterized.

---

### F3 — Database Connectivity

**Where:** `core/db_connector.py`

**Public API:**

```python
connect(db_type, host, port, db, user, password) → Engine
test_connection(engine) → (bool, message)
list_tables(engine) → List[str]           # tables and views
fetch(engine, table, where_str, params, limit=100_000) → DataFrame
```

**Supported DB types** (SQLAlchemy URL schemes):

| Label | SQLAlchemy scheme | Extra package |
|---|---|---|
| PostgreSQL | `postgresql+psycopg2` | `psycopg2` |
| MySQL | `mysql+pymysql` | `pymysql` |
| SQL Server | `mssql+pyodbc` | `pyodbc` |
| SQLite | `sqlite` | built-in |
| Oracle | `oracle+cx_oracle` | `cx_Oracle` |

Connection details persisted in `llm_config.json` under `"database"` key. Password stored plaintext (encryption out of scope).

`list_tables()` uses `sqlalchemy.inspect(engine).get_table_names()` + `get_view_names()` so both tables and views appear.

---

### F4 — Settings Modal

**Where:** `components/settings_modal.py` + `dashboard.py`

A single `dbc.Modal` registered once in `dashboard.py` layout. A ⚙ icon button in the top navbar opens it from any page.

**LLM Tab fields:**
- Provider (dropdown: Ollama / LMStudio / Claude)
- Base URL (text input, shown for Ollama/LMStudio)
- Model Name (text input)
- API Key (password input, shown for Claude)
- Include Sample Data (toggle)

**Database Tab fields:**
- DB Type (dropdown: PostgreSQL / MySQL / SQL Server / SQLite / Oracle)
- Host, Port, Database Name, Username, Password (text inputs)
- "Test Connection" button — calls `db_connector.test_connection()`, shows inline success/error

**Save behaviour:** Clicking Save writes both sections to `llm_config.json` and updates the in-memory Dash stores (`store-llm-config`, `store-db-config`). No page reload required.

On app startup, `dashboard.py` reads both sections from `llm_config.json` and populates the stores.

---

### F5 — Data Quality Score Fix

**Where:** `core/quality_scorer.py` + `pages/page_dashboard.py`

**Current bug:** Score defaults to `0.85` (85%) hardcoded when no LLM exec summary exists. The number is LLM-invented, not computed from actual data.

**Fix — `quality_scorer.compute(profiles: Dict[str, ColumnProfile]) → float`:**

```
base = 1.0
penalties = 0.0
for each profile:
    penalties += (missing_pct / 100) * 0.40    # missing values: up to 40% weight
    if has_outliers:    penalties += 0.01       # outlier presence
    if cardinality == 1: penalties += 0.05      # constant/dead column
per_column_penalty = penalties / num_columns
score = max(0.0, min(1.0, base - per_column_penalty))
```

Result is a float 0.0–1.0. Displayed as `int(score * 100)%`.

In `page_dashboard.py`, call `quality_scorer.compute(profiles)` using the profiles already in the session store — zero extra computation. Pass the result to both the executive summary card and the footer label, replacing the `exec_summary.get('data_quality_score', 0.85)` fallback everywhere.

---

## 4. Error Handling

- DB connection failure: `test_connection()` returns `(False, error_message)` — shown inline in settings modal; never reaches the dashboard
- DB fetch timeout: `fetch()` wraps in try/except, returns empty DataFrame with error logged server-side
- Missing temporal data: if `pd.to_datetime()` fails on resample, fall back to raw categorical axis
- Missing driver package (e.g. `cx_Oracle` not installed): caught at `connect()`, returns actionable message ("Install cx_Oracle to use Oracle")

---

## 5. Out of Scope

- Password encryption / secrets management
- Multi-condition OR logic in WHERE builder (AND only for now)
- Saving named DB connection profiles
- Per-chart manual granularity override
- Connection pooling configuration

---

## 6. Dependencies to Add

```
sqlalchemy
psycopg2-binary    # PostgreSQL
pymysql            # MySQL
pyodbc             # SQL Server
```

Oracle (`cx_Oracle`) is optional — document separately, not in requirements.txt.
