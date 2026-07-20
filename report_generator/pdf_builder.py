"""
pdf_builder.py
--------------
Core PDF assembly engine using ReportLab.

Provides the PDFReport class that manages:
- Page creation (portrait/landscape)
- Header/footer on every page
- Consistent spacing and layout
- Image embedding for charts
- Table rendering
- Text styles
- Bookmark/TOC support
- Two-pass rendering for clickable Table of Contents
"""

from __future__ import annotations

import os
from typing import Optional, List, Tuple, Dict

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, Flowable
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.lib.utils import ImageReader

from report_generator.config import Colors, Fonts, PageLayout, ReportConfig


# ═══════════════════════════════════════════════════════════════════════
#  COLOR DEFINITIONS (ReportLab HexColor)
# ═══════════════════════════════════════════════════════════════════════

CLR_NAVY = HexColor('#0F172A')
CLR_DARK = HexColor('#1E283C')
CLR_CHARCOAL = HexColor('#334155')
CLR_SLATE = HexColor('#475569')
CLR_GRAY = HexColor('#64748B')
CLR_LIGHT_GRAY = HexColor('#94A3B8')
CLR_SILVER = HexColor('#CBD5E1')
CLR_GHOST = HexColor('#E2E8F0')
CLR_SNOW = HexColor('#F1F5F9')
CLR_WHITE = HexColor('#FFFFFF')
CLR_PRIMARY = HexColor('#4F46E5')
CLR_PRIMARY_LIGHT = HexColor('#6366F1')
CLR_ACCENT = HexColor('#7C3AED')
CLR_SUCCESS = HexColor('#059669')
CLR_SUCCESS_LIGHT = HexColor('#22C55E')
CLR_DANGER = HexColor('#E11D4C')
CLR_DANGER_LIGHT = HexColor('#EF4444')
CLR_WARNING = HexColor('#F59E0B')
CLR_INFO = HexColor('#38BDF8')


# ═══════════════════════════════════════════════════════════════════════
#  CUSTOM FLOWABLES
# ═══════════════════════════════════════════════════════════════════════

class GradientDivider(Flowable):
    """A horizontal gradient divider line."""
    def __init__(self, width=495, height=3, colors=None):
        super().__init__()
        self.width = width
        self.height = height
        self.colors = colors or [CLR_PRIMARY, CLR_ACCENT, CLR_INFO]

    def draw(self):
        c = self.canv
        steps = 50
        step_w = self.width / steps
        for i in range(steps):
            t = i / steps
            if t < 0.5:
                t2 = t * 2
                r = self.colors[0].red * (1 - t2) + self.colors[1].red * t2
                g = self.colors[0].green * (1 - t2) + self.colors[1].green * t2
                b = self.colors[0].blue * (1 - t2) + self.colors[1].blue * t2
            else:
                t2 = (t - 0.5) * 2
                r = self.colors[1].red * (1 - t2) + self.colors[2].red * t2
                g = self.colors[1].green * (1 - t2) + self.colors[2].green * t2
                b = self.colors[1].blue * (1 - t2) + self.colors[2].blue * t2
            c.setFillColor(Color(r, g, b))
            c.rect(i * step_w, 0, step_w + 1, self.height, fill=1, stroke=0)


class SectionHeader(Flowable):
    """A styled section header with accent bar."""
    def __init__(self, text, width=495, font_size=18):
        super().__init__()
        self.text = text
        self.width = width
        self.font_size = font_size
        self.height = font_size + 18

    def draw(self):
        c = self.canv
        # Accent bar
        c.setFillColor(CLR_PRIMARY)
        c.roundRect(0, 0, 4, self.height - 4, 2, fill=1, stroke=0)
        # Text
        c.setFillColor(CLR_NAVY)
        c.setFont(Fonts.PRIMARY_BOLD, self.font_size)
        c.drawString(14, 6, self.text)

        # Bookmark & Outline
        key = self.text.replace("-", "_").replace(" ", "_").lower()
        c.bookmarkPage(key)
        c.addOutlineEntry(self.text, key, level=0, closed=False)


class MetricCard(Flowable):
    """A KPI metric card with label and value."""
    def __init__(self, label, value, width=110, height=60, accent_color=None):
        super().__init__()
        self.label = label
        self.value = str(value)
        self.width = width
        self.height = height
        self.accent = accent_color or CLR_PRIMARY

    def draw(self):
        c = self.canv
        # Card background
        c.setFillColor(CLR_SNOW)
        c.setStrokeColor(CLR_GHOST)
        c.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=1)
        # Top accent line
        c.setFillColor(self.accent)
        c.rect(0, self.height - 3, self.width, 3, fill=1, stroke=0)
        # Value
        c.setFillColor(CLR_NAVY)
        c.setFont(Fonts.PRIMARY_BOLD, 20)
        c.drawCentredString(self.width / 2, 22, self.value)
        # Label
        c.setFillColor(CLR_GRAY)
        c.setFont(Fonts.PRIMARY, 8)
        c.drawCentredString(self.width / 2, 8, self.label)


# ═══════════════════════════════════════════════════════════════════════
#  STYLES
# ═══════════════════════════════════════════════════════════════════════

def get_styles() -> dict:
    """Create all paragraph styles used in the report."""
    styles = {}

    styles['Title'] = ParagraphStyle(
        'Title', fontName=Fonts.PRIMARY_BOLD, fontSize=28,
        textColor=CLR_NAVY, leading=34, alignment=TA_CENTER,
        spaceAfter=6
    )

    styles['H1'] = ParagraphStyle(
        'H1', fontName=Fonts.PRIMARY_BOLD, fontSize=22,
        textColor=CLR_NAVY, leading=28, spaceBefore=20, spaceAfter=10
    )

    styles['H2'] = ParagraphStyle(
        'H2', fontName=Fonts.PRIMARY_BOLD, fontSize=16,
        textColor=CLR_CHARCOAL, leading=22, spaceBefore=16, spaceAfter=8
    )

    styles['H3'] = ParagraphStyle(
        'H3', fontName=Fonts.PRIMARY_BOLD, fontSize=13,
        textColor=CLR_SLATE, leading=18, spaceBefore=12, spaceAfter=6
    )

    styles['Body'] = ParagraphStyle(
        'Body', fontName=Fonts.PRIMARY, fontSize=10,
        textColor=CLR_CHARCOAL, leading=15, alignment=TA_JUSTIFY,
        spaceAfter=6
    )

    styles['BodyBold'] = ParagraphStyle(
        'BodyBold', fontName=Fonts.PRIMARY_BOLD, fontSize=10,
        textColor=CLR_NAVY, leading=15, spaceAfter=6
    )

    styles['Small'] = ParagraphStyle(
        'Small', fontName=Fonts.PRIMARY, fontSize=8.5,
        textColor=CLR_GRAY, leading=12, spaceAfter=4
    )

    styles['SmallBold'] = ParagraphStyle(
        'SmallBold', fontName=Fonts.PRIMARY_BOLD, fontSize=8.5,
        textColor=CLR_SLATE, leading=12, spaceAfter=4
    )

    styles['Insight'] = ParagraphStyle(
        'Insight', fontName=Fonts.PRIMARY, fontSize=10,
        textColor=CLR_CHARCOAL, leading=15,
        leftIndent=20, spaceBefore=4, spaceAfter=4,
        bulletIndent=8, bulletFontName=Fonts.PRIMARY_BOLD,
        bulletColor=CLR_PRIMARY
    )

    styles['Recommendation'] = ParagraphStyle(
        'Recommendation', fontName=Fonts.PRIMARY, fontSize=10,
        textColor=CLR_CHARCOAL, leading=15,
        leftIndent=24, spaceBefore=4, spaceAfter=4,
    )

    styles['CoverTitle'] = ParagraphStyle(
        'CoverTitle', fontName=Fonts.PRIMARY_BOLD, fontSize=36,
        textColor=CLR_NAVY, leading=44, alignment=TA_CENTER,
        spaceAfter=8
    )

    styles['CoverSubtitle'] = ParagraphStyle(
        'CoverSubtitle', fontName=Fonts.PRIMARY, fontSize=14,
        textColor=CLR_SLATE, leading=20, alignment=TA_CENTER,
        spaceAfter=4
    )

    styles['TOCEntry'] = ParagraphStyle(
        'TOCEntry', fontName=Fonts.PRIMARY, fontSize=11,
        textColor=CLR_CHARCOAL, leading=20, leftIndent=12,
        spaceBefore=2, spaceAfter=2
    )

    styles['TOCTitle'] = ParagraphStyle(
        'TOCTitle', fontName=Fonts.PRIMARY_BOLD, fontSize=11,
        textColor=CLR_NAVY, leading=20, leftIndent=0,
        spaceBefore=2, spaceAfter=2
    )

    styles['Footer'] = ParagraphStyle(
        'Footer', fontName=Fonts.PRIMARY, fontSize=7.5,
        textColor=CLR_GRAY, leading=10, alignment=TA_CENTER
    )

    return styles


# ═══════════════════════════════════════════════════════════════════════
#  TABLE HELPERS
# ═══════════════════════════════════════════════════════════════════════

def create_data_table(
    headers: List[str],
    rows: List[List[str]],
    col_widths: Optional[List[float]] = None,
    styles_dict: Optional[dict] = None,
    alternate_rows: bool = True,
    header_bg: HexColor = CLR_PRIMARY,
    header_fg: HexColor = CLR_WHITE,
    max_rows: int = 200
) -> Table:
    """Create a professionally styled data table."""
    if not styles_dict:
        styles_dict = get_styles()

    # Build table data with Paragraph objects for wrapping
    header_paras = [
        Paragraph(f'<b>{h}</b>', ParagraphStyle(
            'TH', fontName=Fonts.PRIMARY_BOLD, fontSize=9,
            textColor=header_fg, leading=12, alignment=TA_CENTER
        ))
        for h in headers
    ]

    body_rows = []
    for row in rows[:max_rows]:
        body_rows.append([
            Paragraph(str(cell), ParagraphStyle(
                'TD', fontName=Fonts.PRIMARY, fontSize=8.5,
                textColor=CLR_CHARCOAL, leading=12, alignment=TA_CENTER
            ))
            for cell in row
        ])

    table_data = [header_paras] + body_rows

    if col_widths is None:
        num_cols = len(headers)
        col_widths = [PageLayout.CONTENT_WIDTH / num_cols] * num_cols

    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), header_fg),
        ('FONTNAME', (0, 0), (-1, 0), Fonts.PRIMARY_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, CLR_GHOST),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, header_bg),
    ]

    # Alternating row colors
    if alternate_rows:
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), CLR_SNOW))

    t.setStyle(TableStyle(style_cmds))
    return t


# ═══════════════════════════════════════════════════════════════════════
#  PDF REPORT CLASS
# ═══════════════════════════════════════════════════════════════════════

class PDFReport:
    """
    Main PDF report builder.

    Usage:
        pdf = PDFReport(config, output_path)
        pdf.add_element(Paragraph("Hello", styles['Body']))
        pdf.add_page_break()
        pdf.add_chart("path/to/chart.png", width=400, height=250)
        pdf.build()
    """

    def __init__(self, config: ReportConfig, output_path: str):
        self.config = config
        self.output_path = output_path
        self.elements: List[Flowable] = []
        self.styles = get_styles()
        self._page_count = 0
        self._toc_entries: List[Tuple[str, int]] = []  # (title, page_num)
        self._bookmarks: List[Tuple[str, str]] = []     # (key, title)

    def add_element(self, element: Flowable):
        """Add any ReportLab flowable to the report."""
        self.elements.append(element)

    def add_elements(self, elements: List[Flowable]):
        """Add multiple flowables."""
        self.elements.extend(elements)

    def add_spacer(self, height: float = 12):
        """Add vertical space."""
        self.elements.append(Spacer(1, height))

    def add_page_break(self):
        """Force a new page."""
        self.elements.append(PageBreak())

    def add_section_header(self, text: str, font_size: int = 18):
        """Add a styled section header with accent bar."""
        self.elements.append(Spacer(1, 8))
        self.elements.append(SectionHeader(text, font_size=font_size))
        self.elements.append(Spacer(1, 12))

    def add_gradient_divider(self):
        """Add a horizontal gradient divider."""
        self.elements.append(Spacer(1, 8))
        self.elements.append(GradientDivider(width=PageLayout.CONTENT_WIDTH))
        self.elements.append(Spacer(1, 8))

    def add_paragraph(self, text: str, style_name: str = 'Body'):
        """Add a styled paragraph."""
        style = self.styles.get(style_name, self.styles['Body'])
        self.elements.append(Paragraph(text, style))

    def add_chart(self, image_path: str, width: float = 420, height: float = 260, align: str = 'CENTER'):
        """Embed a chart image."""
        if not os.path.exists(image_path):
            return
        try:
            img = Image(image_path, width=width, height=height)
            img.hAlign = align
            self.elements.append(img)
        except Exception:
            pass

    def add_metric_row(self, metrics: List[Tuple[str, str, Optional[HexColor]]]):
        """Add a row of KPI metric cards."""
        cards = []
        for label, value, color in metrics:
            cards.append(MetricCard(label, value, accent_color=color or CLR_PRIMARY))

        card_widths = [m.width for m in cards]
        t = Table([cards], colWidths=card_widths)
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        t.hAlign = 'CENTER'
        self.elements.append(t)

    def add_data_table(self, headers, rows, col_widths=None, **kwargs):
        """Add a professional data table."""
        t = create_data_table(headers, rows, col_widths, self.styles, **kwargs)
        self.elements.append(t)

    def add_toc_entry(self, title: str, level: int = 0):
        """Register a TOC entry (populated during first-pass build)."""
        self._toc_entries.append((title, level))

    # ── Header/Footer Canvas Handlers ──

    def _draw_header_footer(self, canvas, doc):
        """Draw header and footer on every page."""
        canvas.saveState()
        page_num = doc.page
        w, h = A4

        # ── HEADER ──
        # Thin accent line at top
        canvas.setFillColor(CLR_PRIMARY)
        canvas.rect(0, h - 4, w, 4, fill=1, stroke=0)

        # College name (left)
        canvas.setFont(Fonts.PRIMARY_BOLD, 8)
        canvas.setFillColor(CLR_GRAY)
        canvas.drawString(PageLayout.MARGIN_LEFT, h - 22, self.config.college_short)

        # ResultAI branding (right)
        canvas.setFont(Fonts.PRIMARY_BOLD, 8)
        canvas.setFillColor(CLR_PRIMARY)
        canvas.drawRightString(w - PageLayout.MARGIN_RIGHT, h - 22, "ResultAI Report")

        # Header line
        canvas.setStrokeColor(CLR_GHOST)
        canvas.setLineWidth(0.5)
        canvas.line(PageLayout.MARGIN_LEFT, h - 28, w - PageLayout.MARGIN_RIGHT, h - 28)

        # ── FOOTER ──
        canvas.setStrokeColor(CLR_GHOST)
        canvas.setLineWidth(0.5)
        canvas.line(PageLayout.MARGIN_LEFT, 35, w - PageLayout.MARGIN_RIGHT, 35)

        # Footer text
        canvas.setFont(Fonts.PRIMARY, 7)
        canvas.setFillColor(CLR_LIGHT_GRAY)
        footer_text = f"Generated by {self.config.generated_by}  |  Job ID: {self.config.job_id}  |  Confidential Academic Report"
        canvas.drawString(PageLayout.MARGIN_LEFT, 24, footer_text)

        # Page number (right)
        canvas.setFont(Fonts.PRIMARY_BOLD, 8)
        canvas.setFillColor(CLR_GRAY)
        canvas.drawRightString(w - PageLayout.MARGIN_RIGHT, 24, f"Page {page_num}")

        canvas.restoreState()

    def _draw_cover_page(self, canvas, doc):
        """Cover page has no header/footer."""
        pass

    # ── BUILD ──

    def build(self):
        """Build and save the PDF."""
        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)

        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=PageLayout.MARGIN_LEFT,
            rightMargin=PageLayout.MARGIN_RIGHT,
            topMargin=PageLayout.MARGIN_TOP,
            bottomMargin=PageLayout.MARGIN_BOTTOM,
        )

        doc.build(
            self.elements,
            onFirstPage=self._draw_cover_page,
            onLaterPages=self._draw_header_footer
        )

        return self.output_path
