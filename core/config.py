"""Configuration, constants, themes, and schemas"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import os

# ═══════════════════════════════════════════════════════════════
# COLORS & THEME (Big Four Professional - McKinsey/Deloitte Style)
# ═══════════════════════════════════════════════════════════════
# Primary Palette (Authority & Trust)
NAVY         = "#1A365D"      # Deep navy (primary authority)
CHARCOAL     = "#2D3748"      # Charcoal (secondary dark)
GOLD         = "#D4AF37"      # Strategic gold accent
PRIMARY_BG   = "#F7FAFC"      # Main background (warmer off-white)
CARD_BG      = "#FFFFFF"      # Card background (white)

# Text Colors
TEXT         = "#1A1F2E"      # Primary text (dark navy)
TEXT_LIGHT   = "#6B7280"      # Secondary text (medium gray)
TEXT_MUTED   = "#9CA3AF"      # Muted text (light gray)
BORDER       = "#E5E7EB"      # Subtle borders (light gray)

# Status Colors (Big Four style)
PRIMARY      = NAVY           # Primary accent changed to Navy
SUCCESS      = "#48BB78"      # Strong green (success/healthy)
WARNING      = "#ED8936"      # Professional orange (caution)
DANGER       = "#F56565"      # Professional red (alert)
INFO         = "#3B82F6"      # Professional blue (information)

# Visual Effects
CARD_SHADOW  = "0 2px 8px rgba(0, 0, 0, 0.1)"  # Enhanced shadow
SHADOW_LIGHT = "0 1px 3px rgba(0, 0, 0, 0.08)"
PALETTE      = "Set2"         # Plotly color palette

# ═══════════════════════════════════════════════════════════════
# DESIGN TOKENS (8px Grid System)
# ═══════════════════════════════════════════════════════════════
SPACING_XS   = "4px"
SPACING_SM   = "8px"
SPACING_MD   = "16px"
SPACING_LG   = "24px"
SPACING_XL   = "32px"
SPACING_2XL  = "48px"

# Typography System
FONT_FAMILY  = "'Segoe UI', '-apple-system', 'Helvetica Neue', sans-serif"
FONT_FAMILY_HEADER = "'Segoe UI', 'Arial', sans-serif"

FONT_SIZE_HEADLINE = "32px"   # Page titles (H1)
FONT_SIZE_TITLE    = "24px"   # Section titles (H2)
FONT_SIZE_SUBHEAD  = "18px"   # Subsection titles (H3)
FONT_SIZE_BODY     = "14px"   # Body text
FONT_SIZE_SMALL    = "12px"   # Labels, captions
FONT_SIZE_TINY     = "11px"   # Metadata

FONT_WEIGHT_THIN   = 300
FONT_WEIGHT_NORMAL = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_SEMIBOLD = 600
FONT_WEIGHT_BOLD   = 700

PLOT_LAYOUT = dict(
    paper_bgcolor=CARD_BG,
    plot_bgcolor="#FAFBFC",
    font=dict(color=TEXT, family=FONT_FAMILY, size=12),
    margin=dict(t=60, b=50, l=60, r=30),
    title=dict(font=dict(size=18, color=NAVY, family=FONT_FAMILY_HEADER)),
    xaxis=dict(
        color=TEXT_LIGHT,
        gridcolor="#F0F0F0",
        showgrid=True,
        zeroline=False,
        showline=True,
        linewidth=2,
        linecolor=BORDER
    ),
    yaxis=dict(
        color=TEXT_LIGHT,
        gridcolor="#F0F0F0",
        showgrid=True,
        zeroline=False,
        showline=True,
        linewidth=2,
        linecolor=BORDER
    ),
    legend=dict(
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor=BORDER,
        borderwidth=1,
        font=dict(color=TEXT, family=FONT_FAMILY)
    ),
    hovermode="x unified",
    showlegend=True,
)

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════
DATA_DIR = r"D:\test\data"
DATA_FILE = "data.csv"
DATA_PATH = os.path.join(DATA_DIR, DATA_FILE)
OUTPUT_DIR = r"D:\test\outputs"
CONFIG_DIR = r"D:\test\configs"

# File upload configuration
UPLOAD_DIR = ".cache/user_uploads"
MAX_UPLOAD_SIZE_MB = 50
ALLOWED_FILE_EXTENSIONS = {'csv', 'xls', 'xlsx'}

# Create directories if they don't exist
for d in [OUTPUT_DIR, UPLOAD_DIR]:
    os.makedirs(d, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION DATACLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class FilterConfig:
    """Configuration for a filter control"""
    column: str
    filter_type: str           # 'dropdown', 'slider', 'multi-select'
    label: str
    default_value: Optional[Any] = None

@dataclass
class KPIConfig:
    """Configuration for a KPI card"""
    metric: str
    aggregation: str           # 'sum', 'count', 'mean', 'max', 'unique'
    label: str
    color: str = PRIMARY
    bg_color: str = "#EFF6FF"

@dataclass
class ChartConfig:
    """Configuration for a chart

    Supported chart types:
    - Basic: 'bar', 'line', 'area', 'scatter', 'pie', 'histogram', 'box', 'heatmap'
    - Advanced: 'waterfall', 'funnel', 'sunburst', 'treemap', 'violin', 'bubble', 'gauge'
    - Specialized: 'gantt', 'sankey', '2d-bar', 'cumulative-line', 'stacked-bar'
    """
    chart_id: str
    chart_type: str
    x_column: str
    y_column: str
    groupby_column: Optional[str] = None
    size: str = "1/3"          # '1/3', '2/3', 'full'
    aggregation: str = "sum"
    title: Optional[str] = None

@dataclass
class DashboardConfig:
    """Complete dashboard configuration"""
    filters: List[FilterConfig] = field(default_factory=list)
    kpis: List[KPIConfig] = field(default_factory=list)
    charts: List[ChartConfig] = field(default_factory=list)
    layout_grid: str = "2-col"     # '1-col', '2-col', '3-col'
    reasoning: str = ""             # Why this layout was chosen

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'filters': [{'column': f.column, 'filter_type': f.filter_type, 'label': f.label}
                       for f in self.filters],
            'kpis': [{'metric': k.metric, 'aggregation': k.aggregation, 'label': k.label}
                    for k in self.kpis],
            'charts': [{'chart_id': c.chart_id, 'chart_type': c.chart_type, 'x': c.x_column,
                       'y': c.y_column, 'size': c.size}
                      for c in self.charts],
            'layout_grid': self.layout_grid,
            'reasoning': self.reasoning
        }

@dataclass
class UploadMetadata:
    """User upload metadata"""
    id: str
    filename: str
    uploaded_at: str
    rows: int
    cols: int
    pickle_path: str
    profiles_path: str

@dataclass
class ChartDescription:
    """Cached chart insight"""
    chart_id: str
    description: str
    generated_at: str
    filter_state_hash: str
    chart_type: str
    x_column: str
    y_column: str
