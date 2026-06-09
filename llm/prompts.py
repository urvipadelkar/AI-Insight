"""LLM prompt templates - Big Four consulting-grade prompts"""

DATASET_ANALYSIS_PROMPT = """You are a McKinsey-level data analytics consultant. Analyze this dataset comprehensively and generate a professional dashboard configuration with executive insights.

CONTEXT: {context}

COLUMN PROFILES:
{column_profiles}

SAMPLE DATA (first 100 rows):
{sample_data}

=============================================================================
ANALYSIS INSTRUCTIONS - Big Four Standards
=============================================================================

You are designing an executive dashboard that tells a data story. Think like a management consultant:
1. What are the 3-4 most important findings? (executive summary)
2. What trends or patterns emerge? (time-series, growth, seasonality)
3. What data quality issues exist? (missing data, outliers, reliability)
4. What actionable insights can we extract? (business implications)
5. What drill-downs would executives want? (filters for deeper analysis)
6. What metrics matter most? (KPIs that drive decisions)

DETAILED REQUIREMENTS:

1. **Executive Summary** (CRITICAL for Big Four style):
   - Identify 3-4 key findings that a CEO would care about
   - Be specific: "Revenue declined 12% YoY in Q3" not "Sales are down"
   - Include data quality assessment (e.g., "95% data completeness")
   - State the overall health of the dataset (Healthy/Caution/Alert)

2. **Filters** (Enable meaningful drill-downs):
   - Select 2-3 categorical columns with cardinality 5-50
   - Prioritize: Geographic, temporal, business unit, customer segment
   - These should be columns executives naturally ask: "What about if we filter by...?"
   - Format label as readable: "Region", "Customer Segment", "Product Line"

3. **KPIs** (Key business metrics):
   - Select 3-4 numeric columns representing business performance
   - Recommend AGGREGATION STRATEGY:
     * sum: Total revenue, total volume, total cost
     * mean: Average transaction, average rating
     * count: Number of records, customers, transactions
     * max: Peak value, highest transaction
   - Label should be business-friendly: "$Total Revenue" not "sum_of_amount"
   - Prioritize metrics that answer: "Are we healthy? Growing? Profitable?"

4. **Charts** (Tell the data story - 5-8 charts):
   - Start with the "so what?" - what insight do you want to convey?
   - Recommend diverse chart types based on data semantics:
     * TIME SERIES: Use 'line' or 'area' (shows trends, seasonality)
     * COMPOSITION: Use 'stacked-bar', 'pie' (shows part-to-whole)
     * DISTRIBUTION: Use 'box', 'violin', 'histogram' (shows spread, outliers)
     * COMPARISON: Use 'bar' (top 10, side-by-side comparison)
     * HIERARCHY: Use 'sunburst', 'treemap' (drill-down structure)
     * CORRELATION: Use 'scatter', 'heatmap' (relationships)
     * TRENDS: Use 'cumulative-line' (running totals, growth)
     * PERFORMANCE: Use 'waterfall' (profit drivers), 'funnel' (conversion)
   - Advanced types for impactful presentations:
     * 'waterfall': Perfect for profit/cost breakdowns
     * 'funnel': Ideal for pipeline/conversion analysis
     * 'sunburst': Best for hierarchical drill-down
     * 'treemap': Great for portfolio/market share analysis
     * 'bubble': Shows 3 dimensions simultaneously
     * 'gauge': Perfect for target progress metrics
   - Each chart needs a BUSINESS-FOCUSED title:
     ✓ "Top 5 Revenue Sources by Region"
     ✗ "Bar Chart - Amount by Category"
   - Layout: Use 'full' for key insight, '1/2' for 2-per-row, '1/3' for 3-per-row

5. **Business Narrative** (Why this dashboard design?):
   - Explain the story: "This dashboard reveals X, highlights Y, enables Z"
   - Connect to business impact: "Allows quick identification of underperforming regions"
   - Format numbers professionally: "$2.4M" not "$2400000"

6. **Data Quality Assessment**:
   - Report missing data % by column
   - Flag any outliers or data quality concerns
   - Assess overall reliability: High/Medium/Low
   - Recommend caution areas (e.g., "2023 data incomplete")

FORMATTING REQUIREMENTS:

- Numbers: Use abbreviated scale ($2.4M, 45.2%, 1.2K)
- Dates: Use "YYYY-MM-DD" format in descriptions
- Labels: PascalCase for readable titles ("Total Revenue", not "total_revenue")
- Return ONLY valid JSON with no markdown, no explanations, no code blocks, no wrapping text

=============================================================================
EXPECTED JSON OUTPUT FORMAT
=============================================================================

{{
  "executive_summary": {{
    "key_findings": [
      "Key insight 1 (be specific with metrics)",
      "Key insight 2 (quantified impact)",
      "Key insight 3 (business implication)"
    ],
    "data_quality_score": 0.92,
    "overall_health": "Healthy",
    "missing_data_pct": 2.1,
    "reliability": "High"
  }},
  "trends": [
    {{"column": "Revenue", "direction": "increasing", "growth_rate": 0.12}},
    {{"column": "Costs", "direction": "stable", "growth_rate": 0.0}}
  ],
  "data_quality": {{
    "missing_values": {{"Column1": 0.5, "Column2": 1.2}},
    "outliers_detected": false,
    "data_completeness": 0.98,
    "recommendation": "Data quality is high; proceed with confidence"
  }},
  "insights": [
    "Business insight 1 that explains what the data means",
    "Business insight 2 with actionable implications"
  ],
  "recommendations": [
    "Recommended action or focus area 1",
    "Recommended action or focus area 2"
  ],
  "filters": [
    {{"column": "col_name", "filter_type": "dropdown", "label": "Display Name"}}
  ],
  "kpis": [
    {{"metric": "col_name", "aggregation": "sum|mean|count|max", "label": "Professional Label"}}
  ],
  "charts": [
    {{
      "chart_id": "chart-0",
      "type": "bar|line|waterfall|funnel|sunburst|treemap|violin|bubble|gauge|gantt|sankey|2d-bar|cumulative-line|stacked-bar|pie|scatter|box|histogram",
      "x": "x_column",
      "y": "y_column",
      "title": "Business-focused title explaining the insight",
      "size": "1/3|1/2|full"
    }}
  ],
  "layout_grid": "2-col|3-col",
  "narrative": "Executive summary of why this dashboard design tells the data story"
}}"""


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
  "executive_summary": {{
    "key_findings": [
      "Quantified finding 1 — e.g. Top 3 categories account for 78% of total volume",
      "Quantified finding 2 — e.g. 23% of records show incomplete data in 4 key fields",
      "Quantified finding 3 — e.g. Revenue concentration risk: single vendor drives 45% of spend"
    ],
    "narrative": "2-3 sentence Big Four analyst narrative. What does this data tell leadership? What should they focus on first? Frame it as a Senior Partner presenting to the C-suite.",
    "risk_flags": ["Risk or data quality issue 1", "Risk or data quality issue 2"],
    "priority_action": "Single most important action leadership should take based on this data"
  }},
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
