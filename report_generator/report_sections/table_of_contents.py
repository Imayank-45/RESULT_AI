"""
table_of_contents.py
--------------------
Auto-generated Table of Contents with dot leaders and page numbers.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, PageBreak, Flowable
from reportlab.lib.colors import HexColor

from report_generator.config import Fonts
from report_generator.pdf_builder import (
    PDFReport, CLR_NAVY, CLR_PRIMARY, CLR_SLATE, CLR_GRAY,
    CLR_GHOST, CLR_SNOW, CLR_WHITE, GradientDivider, SectionHeader
)
from report_generator.data_loader import ReportDataset
from report_generator.config import PageLayout


# ═══════════════════════════════════════════════════════════════════════
#  TOC ENTRY FLOWABLE
# ═══════════════════════════════════════════════════════════════════════

class TOCEntry(Flowable):
    """A single TOC entry with dot leaders."""

    def __init__(self, number, title, page_num, indent=0, is_bold=True):
        super().__init__()
        self.number = number
        self.title = title
        self.page_num = page_num
        self.indent = indent
        self.is_bold = is_bold
        self.width = PageLayout.CONTENT_WIDTH
        self.height = 22

    def draw(self):
        c = self.canv
        x = self.indent

        # Section number
        c.setFillColor(CLR_PRIMARY)
        c.setFont(Fonts.PRIMARY_BOLD, 11)
        c.drawString(x, 6, str(self.number))

        # Title
        font = Fonts.PRIMARY_BOLD if self.is_bold else Fonts.PRIMARY
        c.setFillColor(CLR_NAVY if self.is_bold else CLR_SLATE)
        c.setFont(font, 11 if self.is_bold else 10)
        title_x = x + 30
        c.drawString(title_x, 6, self.title)

        # Dot leaders
        title_width = c.stringWidth(self.title, font, 11 if self.is_bold else 10)
        dots_start = title_x + title_width + 8
        dots_end = self.width - 30
        c.setFillColor(CLR_GRAY)
        c.setFont(Fonts.PRIMARY, 8)
        dot_x = dots_start
        while dot_x < dots_end:
            c.drawString(dot_x, 6, ".")
            dot_x += 4

        # Page number
        c.setFont(Fonts.PRIMARY_BOLD, 11)
        c.setFillColor(CLR_PRIMARY)
        c.drawRightString(self.width, 6, str(self.page_num))

        # Bottom line
        c.setStrokeColor(HexColor('#F1F5F9'))
        c.setLineWidth(0.3)
        c.line(0, 0, self.width, 0)

        # Clickable link to section bookmark
        key = self.title.replace("-", "_").replace(" ", "_").lower()
        c.linkRect(
            contents=self.title,
            destinationname=key,
            Rect=(0, 0, self.width, self.height),
            Border='[0 0 0]',
            relative=1
        )


# ═══════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════

# Estimated page numbers for sections (filled during build)
TOC_SECTIONS = [
    ("01", "Executive Summary", 3),
    ("02", "Overall Statistics", 5),
    ("03", "Branch-wise Analysis", 7),
    ("04", "Semester Analysis", 10),
    ("05", "Subject-wise Analysis", 11),
    ("06", "Topper Analysis", 14),
    ("07", "Student Performance Details", 16),
    ("08", "Grade Distribution", 22),
    ("09", "Pass Percentage Analysis", 24),
    ("10", "Backlog Analysis", 25),
    ("11", "Performance Heatmaps", 27),
    ("12", "Risk Analysis", 29),
    ("13", "Improvement Analysis", 31),
    ("14", "Comparison Analysis", 32),
    ("15", "AI-Generated Insights", 34),
    ("16", "AI Recommendations", 37),
]


def render(pdf: PDFReport, dataset: ReportDataset, analytics):
    """Render the Table of Contents page."""

    # Title
    pdf.add_paragraph("TABLE OF CONTENTS", 'CoverTitle')
    pdf.add_spacer(4)
    pdf.add_gradient_divider()
    pdf.add_spacer(16)

    # Compute estimated page numbers based on student count
    n = len(dataset.records)
    offsets = _estimate_pages(n)

    for i, (num, title, _) in enumerate(TOC_SECTIONS):
        page = offsets[i] if i < len(offsets) else 3 + i * 2
        pdf.add_element(TOCEntry(num, title, page, indent=0, is_bold=True))

    pdf.add_spacer(30)

    # Footer note
    pdf.add_paragraph(
        "<i>Note: Page numbers are approximate and may vary based on data volume. "
        "This report contains AI-generated analytics and automatically computed insights.</i>",
        'Small'
    )

    pdf.add_page_break()


def _estimate_pages(n_students: int) -> list:
    """Estimate page numbers for each section based on student count."""
    student_pages = min(n_students, 100) // 2 + 1  # 2 students per page

    pages = [
        3,                          # Executive Summary
        5,                          # Overall Statistics
        6,                          # Branch Analysis
        8,                          # Semester Analysis
        9,                          # Subject Analysis
        12,                         # Topper Analysis
        14,                         # Student Pages start
        14 + student_pages,         # Grade Distribution
        16 + student_pages,         # Pass Percentage
        17 + student_pages,         # Backlog Analysis
        19 + student_pages,         # Heatmaps
        21 + student_pages,         # Risk Analysis
        23 + student_pages,         # Improvement
        24 + student_pages,         # Comparison
        25 + student_pages,         # AI Insights
        28 + student_pages,         # AI Recommendations
    ]
    return pages
