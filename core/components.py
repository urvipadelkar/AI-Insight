"""Reusable Dash components - Big Four Professional Style"""
from dash import html, dcc
from core.config import (TEXT, TEXT_LIGHT, TEXT_MUTED, CARD_BG, CARD_SHADOW,
                         PRIMARY, SUCCESS, WARNING, DANGER, INFO, NAVY, GOLD,
                         BORDER, FONT_FAMILY, FONT_SIZE_BODY, FONT_SIZE_SMALL,
                         SPACING_SM, SPACING_MD, SPACING_LG, FONT_WEIGHT_SEMIBOLD,
                         FONT_WEIGHT_BOLD)

def kpi_card(title: str, value: str, delta: str = "", comparison: str = "",
             trend: str = "neutral", status: str = "healthy",
             color: str = PRIMARY, bg_color: str = "#EFF6FF"):
    """Professional KPI card with trend indicator and comparison

    Args:
        title: Card title
        value: Main metric value
        delta: Change indicator (e.g., "+12%")
        comparison: Comparison text (e.g., "vs. last month")
        trend: "up", "down", "neutral" for arrow indicator
        status: "healthy", "warning", "alert" for status badge
    """
    # Trend arrow
    trend_color = SUCCESS if trend == "up" else (DANGER if trend == "down" else TEXT_MUTED)
    trend_arrow = "▲" if trend == "up" else ("▼" if trend == "down" else "→")

    # Status badge colors
    status_colors = {
        "healthy": ("#DCFCE7", "#15803D"),  # bg, text
        "warning": ("#FEF3C7", "#B45309"),
        "alert": ("#FEE2E2", "#7F1D1D")
    }
    status_bg, status_text = status_colors.get(status, ("#F3F4F6", "#6B7280"))

    return html.Div([
        # Header: Title + Status Badge
        html.Div([
            html.P(title, style={
                "color": TEXT_LIGHT,
                "fontSize": FONT_SIZE_SMALL,
                "margin": "0 0 8px",
                "fontWeight": FONT_WEIGHT_SEMIBOLD,
                "flex": "1"
            }),
            html.Span(status.title(), style={
                "background": status_bg,
                "color": status_text,
                "fontSize": "10px",
                "fontWeight": FONT_WEIGHT_BOLD,
                "padding": "3px 8px",
                "borderRadius": "4px",
                "fontFamily": FONT_FAMILY
            })
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),

        # Main Value
        html.H3(value, style={
            "color": color,
            "margin": "12px 0 8px",
            "fontSize": "32px",
            "fontWeight": FONT_WEIGHT_BOLD,
            "fontFamily": FONT_FAMILY
        }),

        # Trend Indicator + Delta
        html.Div([
            html.Span(f"{trend_arrow} {delta}", style={
                "color": trend_color,
                "fontSize": FONT_SIZE_SMALL,
                "fontWeight": FONT_WEIGHT_SEMIBOLD,
                "display": "flex",
                "alignItems": "center",
                "gap": "4px"
            }),
            html.Span(comparison, style={
                "color": TEXT_MUTED,
                "fontSize": FONT_SIZE_SMALL,
                "marginLeft": "8px"
            })
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={
        "background": bg_color,
        "boxShadow": CARD_SHADOW,
        "borderRadius": "12px",
        "padding": SPACING_LG,
        "flex": "1",
        "minWidth": "180px",
        "borderLeft": f"4px solid {color}"
    })

def executive_summary_card(title: str, findings: list, health_score: float = 0.9,
                            status: str = "healthy", narrative: str = '',
                            risk_flags: list = None, priority_action: str = ''):
    """Professional Big Four executive summary component"""
    status_colors = {
        "healthy": ("#DCFCE7", "#15803D"),
        "caution": ("#FEF3C7", "#B45309"),
        "alert": ("#FEE2E2", "#7F1D1D")
    }
    status_bg, status_text = status_colors.get(status, ("#F3F4F6", "#6B7280"))
    health_pct = int(health_score * 100)
    risk_flags = risk_flags or []

    children = [
        # Header bar
        html.Div([
            html.Div([
                html.Div("EXECUTIVE BRIEFING", style={
                    'fontSize': '9px', 'fontWeight': '800', 'letterSpacing': '0.15em',
                    'color': GOLD, 'marginBottom': '4px',
                }),
                html.H2(title, style={
                    'color': NAVY, 'fontSize': '22px', 'fontWeight': FONT_WEIGHT_BOLD, 'margin': '0',
                }),
            ], style={'flex': '1'}),
            html.Div([
                html.Span("Data Quality Score", style={'color': TEXT_LIGHT, 'fontSize': '10px', 'display': 'block', 'marginBottom': '2px'}),
                html.Span(f"{health_pct}%", style={
                    'background': status_bg, 'color': status_text,
                    'fontSize': '20px', 'fontWeight': '800',
                    'padding': '4px 14px', 'borderRadius': '6px', 'display': 'block',
                }),
            ], style={'textAlign': 'center'}),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'flex-start',
                  'marginBottom': SPACING_LG, 'paddingBottom': SPACING_MD,
                  'borderBottom': f'2px solid {GOLD}'}),
    ]

    # Narrative paragraph (Big Four analyst voice)
    if narrative:
        children.append(html.Div([
            html.P(narrative, style={
                'color': '#1E293B', 'fontSize': '14px', 'lineHeight': '1.8',
                'fontStyle': 'italic', 'margin': '0',
                'borderLeft': f'4px solid {GOLD}',
                'paddingLeft': '16px',
            }),
        ], style={'marginBottom': SPACING_LG}))

    # Key findings
    if findings:
        children.append(html.Div([
            html.Div("KEY FINDINGS", style={
                'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                'color': TEXT_LIGHT, 'marginBottom': '10px',
            }),
            html.Ul([
                html.Li([
                    html.Span("▸ ", style={'color': GOLD, 'fontWeight': '700'}),
                    html.Span(f, style={'color': TEXT, 'fontSize': FONT_SIZE_BODY}),
                ], style={'marginBottom': '8px', 'listStyle': 'none'})
                for f in findings
            ], style={'paddingLeft': '0', 'margin': '0'}),
        ], style={'marginBottom': SPACING_LG if (risk_flags or priority_action) else '0'}))

    # Risk flags
    if risk_flags:
        children.append(html.Div([
            html.Div("RISK FLAGS", style={
                'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                'color': '#B45309', 'marginBottom': '8px',
            }),
            html.Div([
                html.Span(f"⚠ {flag}", style={
                    'display': 'inline-block', 'backgroundColor': '#FEF3C7',
                    'color': '#92400E', 'fontSize': '11px', 'padding': '3px 10px',
                    'borderRadius': '4px', 'marginRight': '8px', 'marginBottom': '6px',
                    'border': '1px solid #FCD34D',
                })
                for flag in risk_flags
            ]),
        ], style={'marginBottom': SPACING_MD if priority_action else '0'}))

    # Priority action
    if priority_action:
        children.append(html.Div([
            html.Div("PRIORITY ACTION", style={
                'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.1em',
                'color': '#1D4ED8', 'marginBottom': '6px',
            }),
            html.P(f"→ {priority_action}", style={
                'color': '#1E40AF', 'fontSize': '13px', 'fontWeight': '600', 'margin': '0',
                'backgroundColor': '#EFF6FF', 'padding': '10px 14px', 'borderRadius': '6px',
                'border': '1px solid #BFDBFE',
            }),
        ]))

    return html.Div(children, style={
        'background': '#FAFBFF',
        'borderLeft': f'5px solid {GOLD}',
        'borderRadius': '8px',
        'padding': SPACING_LG,
        'boxShadow': '0 4px 16px rgba(0,0,0,0.08)',
        'fontFamily': FONT_FAMILY,
    })

def insight_box(text: str, chart_number: int = None):
    """Professional insight text box for below charts

    Args:
        text: Insight description
        chart_number: Optional chart reference number
    """
    return html.Div([
        html.Span(f"Chart {chart_number}: " if chart_number else "", style={
            "color": NAVY,
            "fontWeight": FONT_WEIGHT_SEMIBOLD,
            "fontSize": FONT_SIZE_SMALL
        }),
        html.Span(text, style={
            "color": TEXT,
            "fontSize": FONT_SIZE_BODY,
            "fontFamily": FONT_FAMILY
        })
    ], style={
        "background": "#FAFBFC",
        "borderLeft": f"3px solid {INFO}",
        "padding": f"{SPACING_SM} {SPACING_MD}",
        "borderRadius": "6px",
        "marginTop": SPACING_SM,
        "fontFamily": FONT_FAMILY
    })

def filter_control(label: str, control_id: str, control_component):
    """Professional filter control wrapper"""
    return html.Div([
        html.Label(label, style={
            "color": TEXT,
            "fontSize": FONT_SIZE_SMALL,
            "fontWeight": FONT_WEIGHT_SEMIBOLD,
            "fontFamily": FONT_FAMILY,
            "marginBottom": "6px",
            "display": "block"
        }),
        control_component,
    ], style={"display": "flex", "flexDirection": "column", "gap": SPACING_SM})

def chart_container(chart_id: str, title: str = "", insight: str = ""):
    """Professional chart container with insight text"""
    return html.Div([
        dcc.Graph(id=chart_id),
        insight_box(insight) if insight else None,
    ], style={
        "background": CARD_BG,
        "boxShadow": CARD_SHADOW,
        "borderRadius": "8px",
        "padding": SPACING_MD,
        "flex": "1",
        "minWidth": "320px"
    })

def section_header(title: str, subtitle: str = ""):
    """Professional section header with subtitle"""
    return html.Div([
        html.H2(title, style={
            "color": NAVY,
            "fontSize": "24px",
            "fontWeight": FONT_WEIGHT_BOLD,
            "margin": "0 0 4px",
            "fontFamily": FONT_FAMILY
        }),
        html.P(subtitle, style={
            "color": TEXT_LIGHT,
            "fontSize": FONT_SIZE_BODY,
            "margin": "0 0 16px",
            "fontFamily": FONT_FAMILY
        }) if subtitle else None
    ])
