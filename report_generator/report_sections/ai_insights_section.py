"""
ai_insights_section.py
----------------------
Renders 30–50 AI-generated insights as numbered observations.
"""

from __future__ import annotations

from typing import List

from reportlab.platypus import Paragraph, Spacer, Flowable
from reportlab.lib.colors import HexColor

from report_generator.config import Fonts, PageLayout
from report_generator.pdf_builder import (
    PDFReport, CLR_NAVY, CLR_PRIMARY, CLR_SLATE, CLR_GRAY,
    CLR_GHOST, CLR_SNOW, CLR_WHITE
)
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator.ai_insights import generate_insights


# ═══════════════════════════════════════════════════════════════════════
#  INSIGHT CARD FLOWABLE
# ═══════════════════════════════════════════════════════════════════════

class InsightItem(Flowable):
    """A numbered insight with accent indicator."""

    def __init__(self, number, text, width=495):
        super().__init__()
        self.number = number
        self.text = text
        self.width = width
        self.height = 28

    def wrap(self, availWidth, availHeight):
        # Estimate height based on text length
        lines = max(1, len(self.text) // 80 + 1)
        self.height = 12 + lines * 14
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        y = self.height

        # Number badge
        badge_size = 18
        c.setFillColor(CLR_PRIMARY)
        c.circle(12, y - 12, badge_size / 2, fill=1, stroke=0)
        c.setFillColor(CLR_WHITE)
        c.setFont(Fonts.PRIMARY_BOLD, 7.5)
        c.drawCentredString(12, y - 15, str(self.number))

        # Text
        c.setFillColor(CLR_NAVY)
        c.setFont(Fonts.PRIMARY, 9.5)

        # Simple word wrap
        words = self.text.split()
        lines = []
        current_line = ""
        max_width = self.width - 35
        for word in words:
            test = current_line + " " + word if current_line else word
            if c.stringWidth(test, Fonts.PRIMARY, 9.5) < max_width:
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        text_y = y - 14
        for line in lines:
            c.drawString(28, text_y, line)
            text_y -= 13

        # Bottom separator
        c.setStrokeColor(HexColor('#F1F5F9'))
        c.setLineWidth(0.3)
        c.line(28, 2, self.width, 2)


# ═══════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════

def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render AI Insights section."""

    pdf.add_section_header("AI-GENERATED INSIGHTS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    insights = generate_insights(analytics)

    pdf.add_paragraph(
        f"The AI analytics engine has generated <b>{len(insights)}</b> observations "
        f"based on comprehensive statistical analysis of the academic data. "
        f"These insights are automatically derived from patterns, distributions, and trends.",
        'Body'
    )
    pdf.add_spacer(10)

    for i, insight in enumerate(insights, 1):
        # Clean any emoji/special chars that might break PDF fonts
        clean = insight.replace("🏆", "[TOP]").replace("⚠", "[!]")
        pdf.add_element(InsightItem(i, clean))
        pdf.add_spacer(2)

        # Page break every ~20 insights
        if i % 20 == 0 and i < len(insights):
            pdf.add_page_break()

    pdf.add_page_break()
