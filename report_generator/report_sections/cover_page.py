"""
cover_page.py
-------------
Renders the premium cover page with college branding, department info,
decorative gradients, and ResultAI branding.
"""

from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import Paragraph, Spacer, PageBreak, Flowable

from report_generator.config import ReportConfig, Fonts
from report_generator.pdf_builder import PDFReport, CLR_NAVY, CLR_PRIMARY, CLR_ACCENT, CLR_SLATE, CLR_GRAY, CLR_WHITE, CLR_GHOST, CLR_SNOW, CLR_LIGHT_GRAY
from report_generator.data_loader import ReportDataset


# ═══════════════════════════════════════════════════════════════════════
#  COVER PAGE BACKGROUND FLOWABLE
# ═══════════════════════════════════════════════════════════════════════

class CoverBackground(Flowable):
    """Draws the full cover page background with decorative elements."""

    def __init__(self, config: ReportConfig, dataset: ReportDataset):
        super().__init__()
        self.config = config
        self.dataset = dataset
        self.width = A4[0]
        self.height = A4[1]

    def wrap(self, availWidth, availHeight):
        return (0, 680)

    def draw(self):
        c = self.canv
        w = 495  # Content width

        # ── Top gradient accent bar ──
        for i in range(40):
            t = i / 40
            r = 0.310 * (1 - t) + 0.486 * t
            g = 0.275 * (1 - t) + 0.227 * t
            b = 0.898 * (1 - t) + 0.929 * t
            c.setFillColor(Color(r, g, b))
            c.rect(-50, 675 - i * 1.5, w + 100, 2, fill=1, stroke=0)

        # ── Logo placeholder (geometric diamond) ──
        cx, cy = w / 2, 610
        size = 40
        c.setFillColor(CLR_PRIMARY)
        path = c.beginPath()
        path.moveTo(cx, cy + size)
        path.lineTo(cx + size, cy)
        path.lineTo(cx, cy - size)
        path.lineTo(cx - size, cy)
        path.close()
        c.drawPath(path, fill=1, stroke=0)

        # Inner diamond
        inner = size * 0.55
        c.setFillColor(CLR_WHITE)
        path2 = c.beginPath()
        path2.moveTo(cx, cy + inner)
        path2.lineTo(cx + inner, cy)
        path2.lineTo(cx, cy - inner)
        path2.lineTo(cx - inner, cy)
        path2.close()
        c.drawPath(path2, fill=1, stroke=0)

        # "R" in center
        c.setFillColor(CLR_PRIMARY)
        c.setFont(Fonts.PRIMARY_BOLD, 24)
        c.drawCentredString(cx, cy - 9, "R")

        # ── College Name ──
        c.setFont(Fonts.PRIMARY_BOLD, 22)
        c.setFillColor(CLR_NAVY)
        c.drawCentredString(w / 2, 540, self.config.college_name)

        # ── Department ──
        c.setFont(Fonts.PRIMARY, 13)
        c.setFillColor(CLR_SLATE)
        c.drawCentredString(w / 2, 518, self.config.department)

        # ── Divider Line ──
        c.setStrokeColor(CLR_GHOST)
        c.setLineWidth(1)
        c.line(w / 2 - 80, 500, w / 2 + 80, 500)

        # ── Report Title ──
        c.setFont(Fonts.PRIMARY_BOLD, 30)
        c.setFillColor(CLR_PRIMARY)
        c.drawCentredString(w / 2, 460, "ACADEMIC")
        c.drawCentredString(w / 2, 425, "PERFORMANCE")
        c.drawCentredString(w / 2, 390, "REPORT")

        # ── Subtitle ──
        c.setFont(Fonts.PRIMARY, 12)
        c.setFillColor(CLR_GRAY)
        c.drawCentredString(w / 2, 365, "AI-Powered Comprehensive Analytics Report")

        # ── Decorative line ──
        # Gradient line
        for i in range(200):
            t = i / 200
            r = 0.310 * (1 - t) + 0.220 * t
            g = 0.275 * (1 - t) + 0.741 * t
            b = 0.898 * (1 - t) + 0.973 * t
            c.setFillColor(Color(r, g, b))
            c.rect(w / 2 - 100 + i, 350, 1.5, 2, fill=1, stroke=0)

        # ── Metadata Grid ──
        meta_y = 310
        meta_items = [
            ("Program", self.config.program or "B.Tech."),
            ("Semester", f"Semester {self.dataset.semester}" if self.dataset.semester else "All Semesters"),
            ("Generated", self.dataset.generated_date),
            ("Job ID", self.dataset.job_id[:30] if self.dataset.job_id else "N/A"),
        ]

        # Draw metadata as a clean grid
        c.setFont(Fonts.PRIMARY_BOLD, 9)
        left_x = w / 2 - 160
        right_x = w / 2 + 20
        for i, (label, value) in enumerate(meta_items):
            x = left_x if i % 2 == 0 else right_x
            y = meta_y - (i // 2) * 30

            # Label
            c.setFillColor(CLR_LIGHT_GRAY)
            c.setFont(Fonts.PRIMARY, 8)
            c.drawString(x, y + 10, label.upper())

            # Value
            c.setFillColor(CLR_NAVY)
            c.setFont(Fonts.PRIMARY_BOLD, 11)
            c.drawString(x, y - 4, str(value))

        # ── Bottom branding bar ──
        bar_y = 60
        c.setFillColor(CLR_SNOW)
        c.rect(-50, bar_y - 5, w + 100, 40, fill=1, stroke=0)

        # Bottom accent line
        for i in range(int(w + 100)):
            t = i / (w + 100)
            r = 0.486 * (1 - t) + 0.310 * t
            g = 0.227 * (1 - t) + 0.275 * t
            b = 0.929 * (1 - t) + 0.898 * t
            c.setFillColor(Color(r, g, b))
            c.rect(-50 + i, bar_y - 8, 1.5, 3, fill=1, stroke=0)

        c.setFont(Fonts.PRIMARY_BOLD, 10)
        c.setFillColor(CLR_PRIMARY)
        c.drawCentredString(w / 2, bar_y + 12, "Generated by ResultAI — Automatic AI Report Generator")

        c.setFont(Fonts.PRIMARY, 8)
        c.setFillColor(CLR_GRAY)
        c.drawCentredString(w / 2, bar_y, "Confidential Academic Document  •  For Authorized Use Only")


# ═══════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════

def render(pdf: PDFReport, dataset: ReportDataset, analytics):
    """Render the cover page."""
    cover = CoverBackground(pdf.config, dataset)
    pdf.add_element(cover)
    pdf.add_page_break()
