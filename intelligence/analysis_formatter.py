"""Format LLM analysis results for user-friendly display"""
from core.config import DashboardConfig, ChartConfig, KPIConfig, FilterConfig
from typing import Dict, List, Optional

class AnalysisFormatter:
    """Convert raw LLM analysis to formatted insights for dashboard display"""

    @staticmethod
    def format_analysis(llm_result) -> Dict:
        """Convert DashboardConfig to formatted analysis insights (handles both dict and object formats)"""
        if not llm_result:
            return None

        # Handle both dict and object formats
        reasoning = llm_result.get('reasoning', '') if isinstance(llm_result, dict) else llm_result.reasoning
        charts = llm_result.get('charts', []) if isinstance(llm_result, dict) else llm_result.charts
        kpis = llm_result.get('kpis', []) if isinstance(llm_result, dict) else llm_result.kpis
        filters = llm_result.get('filters', []) if isinstance(llm_result, dict) else llm_result.filters

        return {
            "overview": AnalysisFormatter._generate_overview(llm_result),
            "reasoning": reasoning,
            "charts_analysis": [
                AnalysisFormatter._format_chart_insight(chart)
                for chart in (charts or [])
            ],
            "kpis_analysis": [
                AnalysisFormatter._format_kpi_insight(kpi)
                for kpi in (kpis or [])
            ],
            "filters_analysis": [
                AnalysisFormatter._format_filter_insight(f)
                for f in (filters or [])
            ],
        }

    @staticmethod
    def _generate_overview(config) -> str:
        """Generate dashboard overview text (handles both dict and object formats)"""
        # Handle both dict and object formats
        charts = config.get('charts', []) if isinstance(config, dict) else config.charts
        kpis = config.get('kpis', []) if isinstance(config, dict) else config.kpis
        filters = config.get('filters', []) if isinstance(config, dict) else config.filters

        num_charts = len(charts) if charts else 0
        num_kpis = len(kpis) if kpis else 0
        num_filters = len(filters) if filters else 0

        overview = f"Dashboard with {num_charts} chart{'s' if num_charts != 1 else ''}"

        if num_kpis > 0:
            overview += f", {num_kpis} KPI metric{'s' if num_kpis != 1 else ''}"

        if num_filters > 0:
            overview += f", and {num_filters} filter{'s' if num_filters != 1 else ''} for drill-down analysis"

        return overview + "."

    @staticmethod
    def _format_chart_insight(chart) -> Dict:
        """Generate insight description for a chart (handles both dict and object formats)"""
        # Handle both dict and object formats
        chart_type = chart.get('chart_type') if isinstance(chart, dict) else chart.chart_type
        chart_id = chart.get('chart_id', '') if isinstance(chart, dict) else chart.chart_id
        title = chart.get('title', '') if isinstance(chart, dict) else chart.title
        x_column = chart.get('x_column', '') if isinstance(chart, dict) else chart.x_column
        y_column = chart.get('y_column', '') if isinstance(chart, dict) else chart.y_column
        aggregation = chart.get('aggregation', '') if isinstance(chart, dict) else chart.aggregation

        chart_type_descriptions = {
            'bar': 'categorical comparison',
            'line': 'temporal trend',
            'area': 'cumulative trend over time',
            'scatter': 'relationship and correlation',
            'pie': 'proportion distribution',
            'histogram': 'distribution analysis',
            'box': 'statistical distribution and outliers',
            'heatmap': 'correlation matrix',
        }

        type_desc = chart_type_descriptions.get(chart_type, 'visualization')

        # Generate insight based on chart type and columns
        if chart_type == 'line' or chart_type == 'area':
            insight = f"Shows how {y_column.lower()} changes over {x_column.lower()}, revealing trends and patterns over time."
        elif chart_type == 'bar':
            insight = f"Displays {y_column.lower()} broken down by {x_column.lower()}, enabling comparison across categories."
        elif chart_type == 'scatter':
            insight = f"Illustrates the relationship between {x_column.lower()} and {y_column.lower()}, helping identify correlations."
        elif chart_type == 'pie':
            insight = f"Shows the proportion of {x_column.lower()} in the dataset, useful for understanding distribution."
        elif chart_type == 'histogram':
            insight = f"Reveals the distribution and frequency of {x_column.lower()} values."
        elif chart_type == 'heatmap':
            insight = "Shows correlation strength between numeric variables, with color intensity indicating relationship strength."
        else:
            insight = f"Provides {type_desc} analysis of {x_column.lower()} and {y_column.lower()}."

        return {
            "chart_id": chart_id,
            "title": title or f"{chart_type.title()} Chart",
            "type": chart_type,
            "x_column": x_column,
            "y_column": y_column,
            "aggregation": aggregation,
            "description": f"Analysis of {x_column.lower()} vs {y_column.lower()}",
            "insight": insight,
        }

    @staticmethod
    def _format_kpi_insight(kpi) -> Dict:
        """Generate insight description for a KPI (handles both dict and object formats)"""
        # Handle both dict and object formats
        metric = kpi.get('metric', '') if isinstance(kpi, dict) else kpi.metric
        aggregation = kpi.get('aggregation', '') if isinstance(kpi, dict) else kpi.aggregation
        label = kpi.get('label', '') if isinstance(kpi, dict) else kpi.label

        agg_descriptions = {
            'sum': 'total',
            'mean': 'average',
            'count': 'number of',
            'max': 'maximum',
            'min': 'minimum',
            'unique': 'unique count of',
        }

        agg_desc = agg_descriptions.get(aggregation, aggregation)

        return {
            "metric": metric,
            "aggregation": aggregation,
            "label": label,
            "description": f"Displays the {agg_desc} of {metric.lower()}.",
            "insight": f"Key metric showing {agg_desc} {metric.lower()} across all records (or filtered data).",
        }

    @staticmethod
    def _format_filter_insight(f) -> Dict:
        """Generate insight description for a filter (handles both dict and object formats)"""
        # Handle both dict and object formats
        column = f.get('column', '') if isinstance(f, dict) else f.column
        filter_type = f.get('filter_type', '') if isinstance(f, dict) else f.filter_type
        label = f.get('label', '') if isinstance(f, dict) else f.label

        filter_type_descriptions = {
            'dropdown': 'select single value',
            'date_range': 'select date range',
            'numeric_range': 'select numeric range',
        }

        type_desc = filter_type_descriptions.get(filter_type, filter_type)

        return {
            "column": column,
            "filter_type": filter_type,
            "label": label,
            "description": f"Allows users to {type_desc} for {column.lower()} to drill down into specific data segments.",
            "insight": f"Interactive filter on {column.lower()} enables detailed analysis of data subsets.",
        }

    @staticmethod
    def format_analysis_banner(config: DashboardConfig) -> str:
        """Generate banner text summarizing the analysis"""
        if not config:
            return "Dashboard generated automatically."

        overview = AnalysisFormatter._generate_overview(config)

        # Build reasoning summary
        reasoning = config.reasoning or "Automatically generated dashboard."

        # Combine
        return f"{overview} {reasoning}"

    @staticmethod
    def generate_chart_description(chart: ChartConfig, config: DashboardConfig) -> str:
        """Generate a paragraph describing what a chart shows"""
        insight = AnalysisFormatter._format_chart_insight(chart)
        return insight['insight']

    @staticmethod
    def generate_kpi_description(kpi: KPIConfig) -> str:
        """Generate a tooltip/description for a KPI card"""
        insight = AnalysisFormatter._format_kpi_insight(kpi)
        return insight['insight']

    @staticmethod
    def generate_filter_description(f: FilterConfig) -> str:
        """Generate a tooltip/description for a filter"""
        insight = AnalysisFormatter._format_filter_insight(f)
        return insight['description']
