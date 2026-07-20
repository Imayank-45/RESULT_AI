"""
ai_recommendations.py
---------------------
Renders 20+ AI-generated actionable recommendations with priority levels.
"""

from __future__ import annotations

from typing import List, Dict

from reportlab.platypus import Paragraph, Spacer, Flowable
from reportlab.lib.colors import HexColor

from report_generator.config import Fonts, PageLayout
from report_generator.pdf_builder import (
    PDFReport, CLR_NAVY, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER,
    CLR_WARNING, CLR_SLATE, CLR_GRAY, CLR_GHOST, CLR_SNOW, CLR_WHITE
)
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator.ai_insights import generate_recommendations


# ═══════════════════════════════════════════════════════════════════════
#  RECOMMENDATION CARD FLOWABLE
# ═══════════════════════════════════════════════════════════════════════

class RecommendationCard(Flowable):
    """A single recommendation with priority badge."""

    PRIORITY_COLORS = {
        "HIGH": HexColor('#EF4444'),
        "MEDIUM": HexColor('#F59E0B'),
        "LOW": HexColor('#22C55E'),
    }

    def __init__(self, number, priority, text, width=495):
        super().__init__()
        self.number = number
        self.priority = priority
        self.text = text
        self.width = width
        self.height = 30

    def wrap(self, availWidth, availHeight):
        lines = max(1, len(self.text) // 70 + 1)
        self.height = 16 + lines * 14
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        y = self.height

        # Priority badge
        color = self.PRIORITY_COLORS.get(self.priority, CLR_GRAY)
        badge_w = 42
        badge_h = 14
        badge_x = 0
        badge_y = y - 16

        c.setFillColor(color)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 3, fill=1, stroke=0)
        c.setFillColor(CLR_WHITE)
        c.setFont(Fonts.PRIMARY_BOLD, 6.5)
        c.drawCentredString(badge_x + badge_w / 2, badge_y + 3.5, self.priority)

        # Number
        c.setFillColor(CLR_GRAY)
        c.setFont(Fonts.PRIMARY_BOLD, 9)
        c.drawString(badge_w + 8, badge_y + 2, f"R{self.number}")

        # Text
        c.setFillColor(CLR_NAVY)
        c.setFont(Fonts.PRIMARY, 9.5)

        # Word wrap
        words = self.text.split()
        lines = []
        current_line = ""
        max_width = self.width - 80
        for word in words:
            test = current_line + " " + word if current_line else word
            if c.stringWidth(test, Fonts.PRIMARY, 9.5) < max_width:
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        text_x = badge_w + 35
        text_y = badge_y + 2
        for line in lines:
            c.drawString(text_x, text_y, line)
            text_y -= 13

        # Bottom line
        c.setStrokeColor(HexColor('#F1F5F9'))
        c.setLineWidth(0.3)
        c.line(0, 2, self.width, 2)


# ═══════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════

def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render AI Recommendations section."""

    pdf.add_section_header("AI RECOMMENDATIONS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    recommendations = generate_recommendations(analytics)

    pdf.add_paragraph(
        f"The AI engine has generated <b>{len(recommendations)}</b> actionable recommendations "
        f"based on the analysis findings. Recommendations are prioritized as "
        f"<font color='#EF4444'><b>HIGH</b></font>, "
        f"<font color='#F59E0B'><b>MEDIUM</b></font>, and "
        f"<font color='#22C55E'><b>LOW</b></font> priority.",
        'Body'
    )
    pdf.add_spacer(10)

    # Priority legend
    high_count = sum(1 for r in recommendations if r['priority'] == 'HIGH')
    med_count = sum(1 for r in recommendations if r['priority'] == 'MEDIUM')
    low_count = sum(1 for r in recommendations if r['priority'] == 'LOW')

    pdf.add_paragraph(
        f"Priority Distribution: <font color='#EF4444'><b>{high_count} HIGH</b></font> | "
        f"<font color='#F59E0B'><b>{med_count} MEDIUM</b></font> | "
        f"<font color='#22C55E'><b>{low_count} LOW</b></font>",
        'SmallBold'
    )
    pdf.add_spacer(10)

    # Sort: HIGH first, then MEDIUM, then LOW
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_recs = sorted(recommendations, key=lambda r: priority_order.get(r['priority'], 3))

    for i, rec in enumerate(sorted_recs, 1):
        card = RecommendationCard(i, rec['priority'], rec['text'])
        pdf.add_element(card)
        pdf.add_spacer(3)

        if i % 15 == 0 and i < len(sorted_recs):
            pdf.add_page_break()

    pdf.add_page_break()
