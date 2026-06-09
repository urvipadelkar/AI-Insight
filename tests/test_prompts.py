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
    assert "executive_summary" in result
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
