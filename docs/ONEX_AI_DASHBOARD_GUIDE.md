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
