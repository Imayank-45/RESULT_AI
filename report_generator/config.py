"""
config.py
---------
Design system constants for the AI Report Generator.

Defines the color palette, typography, page dimensions, branding,
header/footer settings, and all visual tokens used throughout the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
#  COLOR PALETTE — Premium corporate design system
# ═══════════════════════════════════════════════════════════════════════

class Colors:
    """Curated color palette inspired by McKinsey/Deloitte analytics reports."""

    # Primary brand
    PRIMARY = (0.310, 0.275, 0.898)         # #4F46E5 — Indigo 600
    PRIMARY_DARK = (0.243, 0.200, 0.812)    # #3E33CF
    PRIMARY_LIGHT = (0.545, 0.514, 0.945)   # #8B83F1

    # Accent
    ACCENT = (0.486, 0.227, 0.929)          # #7C3AED — Violet 600
    ACCENT_LIGHT = (0.659, 0.518, 0.969)    # #A884F7

    # Neutrals (Slate scale)
    NAVY = (0.059, 0.090, 0.165)            # #0F172A — Slate 900
    DARK = (0.118, 0.157, 0.235)            # #1E283C — Slate 800
    CHARCOAL = (0.200, 0.255, 0.345)        # #334155 — Slate 700
    SLATE = (0.282, 0.333, 0.412)           # #475569 — Slate 600
    GRAY = (0.392, 0.451, 0.525)            # #64748B — Slate 500
    LIGHT_GRAY = (0.580, 0.635, 0.706)      # #94A3B8 — Slate 400
    SILVER = (0.796, 0.835, 0.882)          # #CBD5E1 — Slate 300
    GHOST = (0.886, 0.906, 0.937)           # #E2E8F0 — Slate 200
    SNOW = (0.945, 0.961, 0.976)            # #F1F5F9 — Slate 100
    WHITE = (1.0, 1.0, 1.0)

    # Semantic colors
    SUCCESS = (0.022, 0.588, 0.400)         # #059669 — Emerald 600
    SUCCESS_LIGHT = (0.133, 0.773, 0.369)   # #22C55E — Green 500
    DANGER = (0.882, 0.110, 0.298)          # #E11D4C — Rose 600
    DANGER_LIGHT = (0.937, 0.267, 0.267)    # #EF4444 — Red 500
    WARNING = (0.961, 0.620, 0.043)         # #F59E0B — Amber 500
    INFO = (0.220, 0.741, 0.973)            # #38BDF8 — Sky 400

    # Chart palette (10 distinct colors for multi-series charts)
    CHART_PALETTE = [
        (0.310, 0.275, 0.898),   # Indigo
        (0.022, 0.588, 0.400),   # Emerald
        (0.882, 0.110, 0.298),   # Rose
        (0.961, 0.620, 0.043),   # Amber
        (0.220, 0.741, 0.973),   # Sky
        (0.486, 0.227, 0.929),   # Violet
        (0.925, 0.463, 0.145),   # Orange
        (0.047, 0.647, 0.647),   # Teal
        (0.914, 0.282, 0.502),   # Pink
        (0.455, 0.545, 0.110),   # Lime
    ]

    # Grade color mapping
    GRADE_COLORS = {
        'O':  (0.022, 0.588, 0.400),   # Emerald — Outstanding
        'A+': (0.133, 0.773, 0.369),   # Green
        'A':  (0.220, 0.741, 0.973),   # Sky
        'B+': (0.310, 0.275, 0.898),   # Indigo
        'B':  (0.486, 0.227, 0.929),   # Violet
        'C':  (0.961, 0.620, 0.043),   # Amber
        'P':  (0.925, 0.463, 0.145),   # Orange
        'F':  (0.882, 0.110, 0.298),   # Rose — Fail
    }


# ═══════════════════════════════════════════════════════════════════════
#  TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════

class Fonts:
    """Font settings — uses Helvetica (built into ReportLab)."""
    PRIMARY = "Helvetica"
    PRIMARY_BOLD = "Helvetica-Bold"
    PRIMARY_ITALIC = "Helvetica-Oblique"
    PRIMARY_BOLD_ITALIC = "Helvetica-BoldOblique"

    # Font sizes (in points)
    SIZE_TITLE = 28
    SIZE_H1 = 22
    SIZE_H2 = 16
    SIZE_H3 = 13
    SIZE_BODY = 10
    SIZE_SMALL = 8.5
    SIZE_TINY = 7
    SIZE_COVER_TITLE = 36
    SIZE_COVER_SUBTITLE = 14
    SIZE_METRIC = 32
    SIZE_METRIC_LABEL = 9


# ═══════════════════════════════════════════════════════════════════════
#  PAGE DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════

class PageLayout:
    """A4 page dimensions and margins in points (1 pt = 1/72 inch)."""

    # A4 dimensions
    WIDTH = 595.28
    HEIGHT = 841.89

    # Landscape
    LANDSCAPE_WIDTH = 841.89
    LANDSCAPE_HEIGHT = 595.28

    # Margins
    MARGIN_TOP = 60
    MARGIN_BOTTOM = 45
    MARGIN_LEFT = 50
    MARGIN_RIGHT = 50

    # Usable content area
    CONTENT_WIDTH = WIDTH - MARGIN_LEFT - MARGIN_RIGHT          # ~495pt
    CONTENT_HEIGHT = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM        # ~737pt

    # Header/Footer
    HEADER_HEIGHT = 35
    FOOTER_HEIGHT = 25

    # Content start (below header)
    CONTENT_TOP = HEIGHT - MARGIN_TOP - HEADER_HEIGHT           # ~747pt
    CONTENT_BOTTOM = MARGIN_BOTTOM + FOOTER_HEIGHT              # ~70pt


# ═══════════════════════════════════════════════════════════════════════
#  BRANCH CODE MAPPING
# ═══════════════════════════════════════════════════════════════════════

BRANCH_CODES = {
    "IT":   "Information Technology",
    "CS":   "Computer Science & Engineering",
    "AI":   "AI & Machine Learning",
    "EC":   "Electronics & Communication",
    "EE":   "Electrical Engineering",
    "ME":   "Mechanical Engineering",
    "CE":   "Civil Engineering",
    "CH":   "Chemical Engineering",
    "BT":   "Biotechnology",
    "EX":   "Electronics & Instrumentation",
    "FT":   "Food Technology",
    "TX":   "Textile Engineering",
    "MT":   "Metallurgy",
    "AU":   "Automobile Engineering",
    "PH":   "Pharmacy",
    "AR":   "Architecture",
    "MC":   "MCA",
    "MB":   "MBA",
    "PY":   "Physics (Common)",
    "MA":   "Mathematics (Common)",
}


# ═══════════════════════════════════════════════════════════════════════
#  GRADE VALUE MAPPING (for numerical analysis)
# ═══════════════════════════════════════════════════════════════════════

GRADE_POINTS = {
    'O':  10.0,
    'A+': 9.0,
    'A':  8.0,
    'B+': 7.0,
    'B':  6.0,
    'C':  5.0,
    'P':  4.0,
    'F':  0.0,
    'FAIL': 0.0,
    'AB': 0.0,
    'ABSENT': 0.0,
    'RL': 0.0,
}


# ═══════════════════════════════════════════════════════════════════════
#  REPORT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ReportConfig:
    """Full configuration for a single report generation run."""

    # Branding
    college_name: str = "Rajiv Gandhi Proudyogiki Vishwavidyalaya"
    college_short: str = "RGPV"
    department: str = "Department of Information Technology"
    semester: str = ""
    program: str = "B.Tech."
    logo_path: Optional[str] = None

    # Job metadata
    job_id: str = ""
    generated_by: str = "ResultAI v1.0"

    # Report settings
    max_student_pages: int = 100       # Cap individual student pages
    students_per_page: int = 2         # Students per detail page
    top_n_students: int = 20           # Topper list size
    max_insights: int = 50             # Max AI insights to generate
    max_recommendations: int = 25      # Max AI recommendations

    # Chart settings
    chart_dpi: int = 200               # Chart resolution
    chart_style: str = "dark"          # "dark" or "light"

    # Output
    output_dir: str = "data/reports"
