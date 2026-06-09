"""Generic chart callback factory"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output
from core.config import ChartConfig, PLOT_LAYOUT, PALETTE
import numpy as np

def register_chart_callbacks(app, df: pd.DataFrame, chart_configs: list, filter_col: str = None):
    """Register callbacks for all charts"""

    for config in chart_configs:
        if config.chart_type == 'heatmap':
            register_correlation_callback(app, df, config)
        else:
            register_standard_chart_callback(app, df, config, filter_col)

def register_standard_chart_callback(app, df: pd.DataFrame,
                                   config: ChartConfig, filter_col: str = None):
    """Register callback for standard charts"""

    @app.callback(
        Output(config.chart_id, "figure"),
        [Input('filter-value', 'value')] if filter_col else []
    )
    def update_chart(filter_value=None):
        """Update chart based on filters"""
        fdf = df

        # Apply filter if provided
        if filter_col and filter_value and filter_value != "All":
            fdf = df[df[filter_col] == filter_value]

        # Skip if columns don't exist
        if config.x_column not in fdf.columns or config.y_column not in fdf.columns:
            return go.Figure()

        try:
            # Prepare data
            y_col = config.y_column  # Default to y_column
            aggregation = config.aggregation or 'sum'  # Default aggregation

            # For charts needing aggregation (expanded list)
            needs_aggregation = config.chart_type in ['bar', 'line', 'area', 'pie', 'box', 'waterfall',
                                                      'funnel', 'stacked-bar', 'cumulative-line', '2d-bar']

            if needs_aggregation and aggregation != 'raw':
                if aggregation == 'sum':
                    gdf = fdf.groupby(config.x_column)[config.y_column].sum().reset_index()
                elif aggregation == 'mean':
                    gdf = fdf.groupby(config.x_column)[config.y_column].mean().reset_index()
                elif aggregation == 'count':
                    # For count, use a named aggregation to avoid duplicate column names
                    if config.x_column == config.y_column:
                        gdf = fdf.groupby(config.x_column).size().reset_index(name='count')
                        y_col = 'count'
                    else:
                        gdf = fdf.groupby(config.x_column)[config.y_column].count().reset_index()
                        y_col = config.y_column
                elif aggregation == 'max':
                    gdf = fdf.groupby(config.x_column)[config.y_column].max().reset_index()
                else:
                    gdf = fdf
            else:
                gdf = fdf

            # Debug logging
            print(f"[DEBUG] Chart {config.chart_id}: agg={config.aggregation}, x={config.x_column}, y={y_col}")
            print(f"[DEBUG] Grouped data shape: {gdf.shape}, columns: {gdf.columns.tolist()}")
            if len(gdf) > 0:
                print(f"[DEBUG] First 3 rows:\n{gdf.head(3)}")

            # Create figure based on type
            if config.chart_type == 'bar':
                fig = px.bar(gdf, x=config.x_column, y=y_col,
                           color_discrete_sequence=px.colors.qualitative.Set2)
            elif config.chart_type == 'line':
                fig = px.line(gdf, x=config.x_column, y=y_col)
            elif config.chart_type == 'area':
                fig = px.area(gdf, x=config.x_column, y=y_col)
            elif config.chart_type == 'scatter':
                fig = px.scatter(fdf, x=config.x_column, y=config.y_column)
            elif config.chart_type == 'pie':
                fig = px.pie(gdf, names=config.x_column, values=y_col,
                           color_discrete_sequence=px.colors.qualitative.Set2)
            elif config.chart_type == 'histogram':
                fig = px.histogram(fdf, x=config.x_column, nbins=30)
            elif config.chart_type == 'box':
                fig = px.box(fdf, x=config.x_column, y=config.y_column)

            # Advanced chart types
            elif config.chart_type == 'waterfall':
                # Waterfall: shows cumulative contribution (useful for profit, cost breakdowns)
                fig = go.Figure(data=[go.Waterfall(
                    x=gdf[config.x_column], y=gdf[y_col],
                    measure=["relative"] * len(gdf),
                    text=gdf[y_col].round(1), textposition="outside",
                    connector={"line": {"color": "rgba(63, 63, 63, 0.5)"}}
                )])

            elif config.chart_type == 'funnel':
                # Funnel: shows conversion/pipeline stages (sales funnel, attrition)
                fig = px.funnel(gdf, x=y_col, y=config.x_column,
                              color_discrete_sequence=px.colors.qualitative.Set2)

            elif config.chart_type == 'sunburst':
                # Sunburst: hierarchical pie chart (nested categories)
                if hasattr(config, 'groupby_column') and config.groupby_column:
                    gdf_hier = fdf.groupby([config.groupby_column, config.x_column])[config.y_column].sum().reset_index()
                    fig = px.sunburst(gdf_hier, labels=config.x_column, parents=config.groupby_column,
                                    values=config.y_column, color_discrete_sequence=px.colors.qualitative.Set2)
                else:
                    fig = px.sunburst(gdf, labels=config.x_column, values=y_col,
                                    color_discrete_sequence=px.colors.qualitative.Set2)

            elif config.chart_type == 'treemap':
                # Treemap: area-based hierarchy (market share, portfolio composition)
                if hasattr(config, 'groupby_column') and config.groupby_column:
                    gdf_hier = fdf.groupby([config.groupby_column, config.x_column])[config.y_column].sum().reset_index()
                    fig = px.treemap(gdf_hier, labels=config.x_column, parents=config.groupby_column,
                                   values=config.y_column, color_discrete_sequence=px.colors.qualitative.Set2)
                else:
                    fig = px.treemap(gdf, labels=config.x_column, values=y_col,
                                   color_discrete_sequence=px.colors.qualitative.Set2)

            elif config.chart_type == 'violin':
                # Violin: distribution comparison (statistical spread, outliers)
                fig = px.violin(fdf, x=config.x_column, y=config.y_column, box=True, points=False)

            elif config.chart_type == 'bubble':
                # Bubble: 3-variable scatter (needs 3rd numeric column - uses count as size)
                bubble_size = fdf.groupby(config.x_column).size()
                bubble_df = gdf.copy()
                bubble_df['size'] = bubble_df[config.x_column].map(bubble_size)
                fig = px.scatter(bubble_df, x=config.x_column, y=y_col, size='size',
                               color_discrete_sequence=px.colors.qualitative.Set2)

            elif config.chart_type == 'gauge':
                # Gauge: KPI progress toward 100% target (needs numeric 0-100)
                value = gdf[y_col].iloc[0] if len(gdf) > 0 else 0
                fig = go.Figure(data=[go.Indicator(
                    mode="gauge+number+delta", value=min(value, 100),
                    domain={'x': [0, 1], 'y': [0, 1]},
                    gauge={'axis': {'range': [0, 100]},
                           'bar': {'color': "#3B82F6"},
                           'steps': [
                               {'range': [0, 50], 'color': "rgba(255, 193, 7, 0.2)"},
                               {'range': [50, 100], 'color': "rgba(76, 175, 80, 0.2)"}
                           ]},
                    title={'text': config.title or "Progress"}
                )])

            elif config.chart_type == 'gantt':
                # Gantt: timeline visualization (project milestones, durations)
                if pd.api.types.is_datetime64_any_dtype(fdf[config.x_column]):
                    fig = px.timeline(fdf, x_start=config.x_column, x_end=config.y_column,
                                    y=config.x_column)
                else:
                    # Fallback for non-datetime
                    fig = px.bar(gdf, x=config.x_column, y=y_col)

            elif config.chart_type == 'sankey':
                # Sankey: flow diagram (resource allocation, customer journey)
                # Simple version: uses groupby to show flows
                gdf_flow = fdf.groupby(config.x_column)[config.y_column].sum().reset_index()
                fig = go.Figure(data=[go.Sankey(
                    node=dict(pad=15, line=dict(color="black", width=0.5),
                             label=gdf_flow[config.x_column].tolist()),
                    link=dict(source=list(range(len(gdf_flow))),
                             target=[0] * len(gdf_flow),
                             value=gdf_flow[y_col].tolist())
                )])

            elif config.chart_type == '2d-bar':
                # 2D bar: cross-tabulation (Marimekko-style)
                if hasattr(config, 'groupby_column') and config.groupby_column:
                    fig = px.bar(fdf, x=config.x_column, y=config.y_column,
                               color=config.groupby_column, barmode='group',
                               color_discrete_sequence=px.colors.qualitative.Set2)
                else:
                    fig = px.bar(gdf, x=config.x_column, y=y_col,
                               color_discrete_sequence=px.colors.qualitative.Set2)

            elif config.chart_type == 'cumulative-line':
                # Cumulative line: running total trend
                gdf['cumulative'] = gdf[y_col].cumsum()
                fig = px.line(gdf, x=config.x_column, y='cumulative',
                            markers=True, title=config.title or "Cumulative Total")

            elif config.chart_type == 'stacked-bar':
                # Stacked bar: composition breakdown
                if hasattr(config, 'groupby_column') and config.groupby_column:
                    fig = px.bar(fdf.groupby([config.x_column, config.groupby_column])[config.y_column].sum().reset_index(),
                               x=config.x_column, y=config.y_column,
                               color=config.groupby_column,
                               color_discrete_sequence=px.colors.qualitative.Set2)
                else:
                    fig = px.bar(gdf, x=config.x_column, y=y_col,
                               color_discrete_sequence=px.colors.qualitative.Set2)

            else:
                # Default fallback
                fig = px.bar(gdf, x=config.x_column, y=y_col)

            # Apply professional layout
            title = config.title or f"{config.chart_type.title()} - {config.y_column}"
            fig.update_layout(title=title, **PLOT_LAYOUT)

            return fig
        except Exception as e:
            print(f"[ERROR] Chart {config.chart_id} error: {e}")
            import traceback
            traceback.print_exc()
            return go.Figure()

def register_correlation_callback(app, df: pd.DataFrame, config: ChartConfig):
    """Register callback for correlation heatmap"""

    @app.callback(
        Output(config.chart_id, "figure"),
        []
    )
    def update_correlation():
        """Update correlation heatmap"""
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

            if len(numeric_cols) < 2:
                return go.Figure()

            # Calculate correlation
            corr = df[numeric_cols].corr().round(2)

            # Create heatmap
            fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r",
                          zmin=-1, zmax=1)
            fig.update_layout(title="Correlation Matrix", **PLOT_LAYOUT)

            return fig
        except Exception as e:
            print(f"[ERROR] Correlation chart error: {e}")
            return go.Figure()
