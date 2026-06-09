# Dashboard Upgrade Design — 2026-04-18

## Summary

Four coordinated improvements to the Onex AI Data Insight dashboard:

1. **Objective field** — user-supplied analysis goal injected into every LLM call
2. **Performance fixes** — eliminate per-navigation re-profiling and per-call type coercion
3. **Security fixes** — stop exposing raw exception details in the browser UI; add input guard on Objective
4. **Housekeeping** — delete 14 stale files, fix redundant code, consolidate 7 docs into one manual, update CLAUDE.md and memory

---

## Section 1: Objective Field

### What it does

A free-text input on the Configure Dashboard page where the user states what they want to learn from the data before running AI analysis. Example: *"Check monthly trend of expense and performance of the posters."*

The text is passed into every LLM call as a top-level instruction, steering chart type selection, KPI focus, and the strategic narrative toward the user's stated goal.

### UI Change — `pages/page_config.py`

Inside the existing **AI Suggestions** card, add above the "Get AI Suggestions" button:

```
+-----------------------------------------------+
| AI Suggestions                                 |
|                                                |
| ANALYSIS OBJECTIVE (optional)                  |
| +-------------------------------------------+ |
| | e.g. Check monthly trend of expense and   | |
| | performance of the posters                | |
| +-------------------------------------------+ |
|                                                |
| [Get AI Suggestions]                           |
+-----------------------------------------------+
```

Component: `dcc.Textarea(id='objective-input', maxLength=500, rows=3)`

A new callback in `page_config.py` syncs the textarea value to `store-objective`.

### Store — `dashboard.py` app layout

Add alongside existing stores:
```python
dcc.Store(id='store-objective', storage_type='memory', data='')
```

`storage_type='memory'` — lives for the session, resets on page refresh. Appropriate for a one-run analysis goal.

### Prompt refactor — `llm/prompts.py`

Move the 60-line Big Four analyst prompt out of `dashboard.py`'s `analyze_with_ai` callback into a new function:

```python
def build_big_four_prompt(col_summary, sample_str, n_rows, n_cols,
                           n_kpis, n_filters, objective='') -> str:
```

When `objective` is non-empty, prepend to the prompt:
```
USER OBJECTIVE: {objective}

Use this objective to prioritise chart types, KPI selection, and the strategic narrative.
Focus your recommendations on answering: "{objective}"
```

### Callback changes — `dashboard.py`

Both `analyze_with_ai` and `refresh_dashboard_analysis` gain:
```python
State('store-objective', 'data')
```
and pass `objective` into `build_big_four_prompt(...)`.

The `session_state` sync callback also includes objective:
```python
if objective:
    session_data['objective'] = objective
```

---

## Section 2: Performance Fixes

### Fix 1 — `display_page` re-profiling on every navigation

**Problem:** `display_page` currently calls `DataProfiler().profile(current_df)` on every URL change, including every filter interaction that triggers a re-render. On a 61k-row, 33-column dataset this is measurably slow.

**Fix:** Replace the live `profiler.profile()` call with a read from `profiles_json_path` (already written at startup and refreshed on upload). The `load_cached_profiles()` function already exists for this purpose.

```python
# Before
current_profiles_obj = profiler.profile(current_df)
current_profiles = {name: {...} for name, p in current_profiles_obj.items()}

# After
current_profiles = load_cached_profiles()
```

For user uploads: the upload handler (`page_upload.py`) already writes a fresh profiles JSON — the cache is always current.

### Fix 2 — `get_cached_dataframe()` per-call type coercion

**Problem:** The currency/comma stripping + `pd.to_numeric` coercion loop iterates all columns on every chart update callback (every filter change triggers multiple chart callbacks). The frame is already on disk after startup coercion — there is no need to re-coerce on every read.

**Fix:** Apply coercion once at startup (already happens for `Amount` column at lines 121-129 of `dashboard.py`) and generalise it to all string-numeric columns before writing to disk. `get_cached_dataframe()` then simply loads and returns the already-clean frame.

For user uploads: apply the same coercion inside the upload handler before saving, so the stored frame is always clean.

Remove the redundant coercion loop from `get_cached_dataframe()` once the above is in place.

---

## Section 3: Security Fixes

### Fix 1 — Raw exceptions exposed in browser UI

**Problem:** `display_page` and `analyze_with_ai` both render `f"{type(e).__name__}: {str(e)}"` directly into HTML returned to the browser. This can leak:
- Internal file paths
- Column names and data values
- Stack trace fragments

**Fix:** In all `except` blocks that render to the UI:
```python
# Log full detail server-side
print(f"[ERROR] {type(e).__name__}: {e}\n{traceback.format_exc()}")

# Show generic message in browser
html.P("An error occurred. Check server logs for details.")
```

Applies to: `display_page`, `analyze_with_ai`, `refresh_dashboard_analysis`.

### Fix 2 — Objective input length guard

**Problem:** The Objective textarea is injected directly into the LLM prompt string. An oversized or crafted input could bloat token usage or attempt prompt injection.

**Fix:** Server-side truncation before injection:
```python
objective = (objective or '')[:500].strip()
```

The `dcc.Textarea(maxLength=500)` provides client-side enforcement; the server-side strip is the authoritative guard.

---

## Section 4: Code Cleanup

### Files to delete (14 total)

**Test files (5):**
- `test_callbacks.py`
- `test_plot.py`
- `test_system.py`
- `test_dashboard_init.py`
- `test_llm_improvement.py`

**Stale documentation (7):**
- `IMPLEMENTATION_SUMMARY.md`
- `IMPLEMENTATION_CHECKLIST.md`
- `IMPROVEMENTS.md`
- `TEST_RESULTS.md`
- `FIX_SUMMARY.md`
- `TRANSFORMATION_SUMMARY.md`
- `OLLAMA_TROUBLESHOOTING.md`

**Malformed files (3):**
- `D:testpages__init__.py`
- `D:testTEST_CHECKLIST.md`
- `D:testLLM_DATA_PRIVACY.md`

### Redundant code to fix

**`dashboard.py`:**
- Remove duplicate docstring on `display_page` (line 502 is a verbatim repeat of line 495)
- Remove unused `section_header` from the `core.components` import (line 38)
- Remove unused `register_chart_callbacks` import (line 47) — imported but never called
- Move `provider = None` initialisation to before the outer `try` block so line 349's reference is always safe

**`core/config.py`:**
- Remove `CONFIG_DIR` from the `os.makedirs` loop — the configs directory is never written to by any current code path

---

## Section 5: Documentation

### Single manual — `docs/ONEX_AI_DASHBOARD_GUIDE.md`

Replaces all 7 deleted stale docs. Structure:

| Chapter | Content |
|---|---|
| 1. Overview | 4-phase architecture diagram, tech stack table |
| 2. Setup | Install deps, configure `llm_config.json`, run `python dashboard.py` |
| 3. Usage Flow | Upload -> Review Data -> Configure Dashboard (Objective field) -> Dashboard |
| 4. LLM Providers | Ollama, LMStudio, Claude — config JSON examples, fallback chain |
| 5. Developing | Add chart type, add LLM provider, debug data profiling |
| 6. Data Reference | Count aggregation pattern, temporal detection, numeric coercion, upload format |
| 7. Troubleshooting | LLM connection errors, encoding errors, module import errors |

---

## Section 6: CLAUDE.md Updates

**Remove:** "Recent Fixes" section — these are historical, not useful as living instructions.

**Add to Phase 4 description:** Objective field — `dcc.Textarea` on config page, synced to `store-objective`, injected into all LLM calls via `build_big_four_prompt()` in `llm/prompts.py`.

**Update file structure tree:** Remove deleted files, add `docs/ONEX_AI_DASHBOARD_GUIDE.md`.

**Update "Notes for Claude":**
- Reference `docs/ONEX_AI_DASHBOARD_GUIDE.md` as the single source of truth for setup/usage
- Add: "Objective field is stored in `store-objective` (memory store); always pass to `build_big_four_prompt()` as `objective` parameter"
- Add: "Never render raw exception details in Dash UI callbacks — log server-side, show generic message in browser"

---

## Section 7: Memory Updates

| File | Change |
|---|---|
| `project_4phase_dashboard.md` | Add Objective field to Phase 4 description; update file structure |
| `feedback_error_handling.md` | New: never expose raw `str(e)` in Dash UI; log server-side only |
| `project_dashboard_transformation.md` | Mark housekeeping complete; note doc consolidated to `docs/ONEX_AI_DASHBOARD_GUIDE.md` |

---

## Implementation Order

1. Delete 14 stale files
2. Fix redundant code in `dashboard.py` and `core/config.py`
3. Refactor prompt to `llm/prompts.py` — `build_big_four_prompt()`
4. Add `store-objective` to app layout
5. Add Objective textarea + sync callback to `page_config.py`
6. Wire `State('store-objective')` into `analyze_with_ai` and `refresh_dashboard_analysis`
7. Apply performance fixes (display_page profiling, get_cached_dataframe coercion)
8. Apply security fixes (error handling, input guard)
9. Write `docs/ONEX_AI_DASHBOARD_GUIDE.md`
10. Update `CLAUDE.md`
11. Update memory files

## Files Modified

| File | Change type |
|---|---|
| `dashboard.py` | Refactor prompt out, add store-objective, fix error handling, fix provider init, remove unused import |
| `pages/page_config.py` | Add Objective textarea + sync callback |
| `llm/prompts.py` | Add `build_big_four_prompt()` function |
| `core/config.py` | Remove CONFIG_DIR from makedirs loop |
| `CLAUDE.md` | Update per Section 6 |
| `docs/ONEX_AI_DASHBOARD_GUIDE.md` | New file |
| Memory files (3) | Update per Section 7 |
