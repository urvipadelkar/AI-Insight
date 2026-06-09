"""
Chart Analyzer - Use LLM to generate insights for charts
"""

from typing import Optional


class ChartAnalyzer:
    """Analyze charts with LLM to generate insights"""

    def __init__(self, provider=None, config=None):
        self.provider = provider
        self.config = config
        self.cache = {}  # Simple in-memory cache for insights

    def analyze_chart(self,
                     chart_type: str,
                     x_column: str,
                     y_column: str,
                     aggregation: str,
                     filtered_data_sample: str,
                     chart_title: str = None) -> str:
        """Generate insight description for a chart

        Args:
            chart_type: bar, line, pie, etc.
            x_column: X-axis column name
            y_column: Y-axis column name (or metric)
            aggregation: sum, count, mean, max, etc.
            filtered_data_sample: JSON string of sample data rows
            chart_title: Optional chart title

        Returns:
            2-3 sentence insight description (or fallback message)
        """
        if not self.provider:
            return "AI insights require LLM configuration"

        # Check cache
        cache_key = f"{chart_type}_{x_column}_{y_column}_{aggregation}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            prompt = f"""Analyze this chart briefly and provide 1-2 sentence insight.

Chart Type: {chart_type}
X-Axis: {x_column}
Y-Axis/Metric: {y_column}
Aggregation: {aggregation}
Title: {chart_title or 'N/A'}

Sample Data:
{filtered_data_sample}

Provide specific insight about trends, patterns, top values, or anomalies. Be concise (1-2 sentences, max 150 words)."""

            # Call LLM using raw generation (no dataset analysis template)
            response = self.provider.generate_text(prompt)
            insight = response.strip()[:300]  # Limit length

            # Cache result
            self.cache[cache_key] = insight

            return insight

        except Exception as e:
            print(f"[WARN] Chart analysis failed: {e}")
            return f"Unable to analyze chart"

    def narrate_insight(self, title: str, chart_type: str, x_col: str, y_col: str,
                        stats_summary: str, data_text: str = "") -> Optional[str]:
        """Turn a statistical summary into a 1-sentence business narrative via LLM.

        Returns None on failure so the caller can fall back to the raw stats.
        """
        if not self.provider:
            return None

        cache_key = f"narrate_{title}_{chart_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        cols_line = ""
        if x_col:
            cols_line = f"X-axis column: {x_col}"
            if y_col and y_col != x_col:
                cols_line += f" | Y-axis column: {y_col}"

        data_section = (
            f"\nACTUAL CHART DATA (ground truth — use ONLY these values):\n{data_text}\n"
            if data_text else ""
        )

        prompt = (
            f'You are converting a data summary into one plain-English sentence.\n\n'
            f'Chart: "{title}" ({chart_type}) | {cols_line}\n'
            f'{data_section}'
            f'COMPUTED STATISTICS (ground truth):\n{stats_summary}\n\n'
            f'STRICT RULES — violating any rule makes the output worthless:\n'
            f'- Write exactly ONE sentence (max 35 words)\n'
            f'- Use ONLY numbers, percentages, and names that appear in the data or statistics above\n'
            f'- Do NOT invent any vendor names, category names, or values not listed above\n'
            f'- Do NOT mention time periods (year-over-year, quarterly, "this year") unless explicit dates appear above\n'
            f'- Do NOT add business interpretations not supported by the numbers above\n'
            f'- If the top item is named exactly in the data, use that exact name\n'
            f'- Do NOT wrap your answer in quotes\n\n'
            f'Sentence (facts only, no invention):'
        )

        try:
            response = self.provider.generate_text(prompt)
            # Take first non-empty line, strip leading "Insight:" if model echoed it
            lines = [l.strip() for l in response.strip().splitlines() if l.strip()]
            insight = lines[0] if lines else ""
            if insight.lower().startswith("insight:"):
                insight = insight[8:].strip()
            insight = insight[:300]
            self.cache[cache_key] = insight
            return insight or None
        except Exception as e:
            print(f"[WARN] narrate_insight failed for '{title}': {e}")
            return None

    def clear_cache(self):
        """Clear analysis cache (call on filter change)"""
        self.cache.clear()
