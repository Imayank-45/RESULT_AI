"""
student_pages.py
----------------
Individual student detail pages — 2 students per page with grades,
SGPA, CGPA, result status, and a mini performance indicator.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.colors import HexColor

from report_generator.config import Fonts, PageLayout, GRADE_POINTS
from report_generator.pdf_builder import (
    PDFReport, CLR_NAVY, CLR_PRIMARY, CLR_SUCCESS, CLR_SUCCESS_LIGHT,
    CLR_DANGER, CLR_DANGER_LIGHT, CLR_WARNING, CLR_SLATE, CLR_GRAY,
    CLR_GHOST, CLR_SNOW, CLR_WHITE, GradientDivider
)
from report_generator.data_loader import ReportDataset, StudentRecord
from report_generator.analytics_engine import AnalyticsResult


# ═══════════════════════════════════════════════════════════════════════
#  STUDENT CARD FLOWABLE
# ═══════════════════════════════════════════════════════════════════════

class StudentCard(Flowable):
    """A single student's detail card with grades and performance summary."""

    def __init__(self, record: StudentRecord, rank: int, program: str, semester: str):
        super().__init__()
        self.record = record
        self.rank = rank
        self.program = program
        self.semester = semester
        self.width = PageLayout.CONTENT_WIDTH
        self.height = 310  # Will adjust based on subjects

    def wrap(self, availWidth, availHeight):
        n_subjects = len(self.record.subjects)
        self.height = 150 + max(n_subjects * 16, 32)
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        r = self.record
        w = self.width
        y = self.height

        # ── Card Border ──
        c.setStrokeColor(CLR_GHOST)
        c.setLineWidth(0.75)
        c.setFillColor(CLR_WHITE)
        c.roundRect(0, 0, w, y, 8, fill=1, stroke=1)

        # ── Top accent bar ──
        result_color = CLR_SUCCESS if r.result == "PASS" else CLR_DANGER if r.result == "FAIL" else CLR_WARNING
        c.setFillColor(result_color)
        c.rect(0, y - 4, w, 4, fill=1, stroke=0)

        # ── Header row: Name + Enrollment ──
        header_y = y - 30
        c.setFont(Fonts.PRIMARY_BOLD, 13)
        c.setFillColor(CLR_NAVY)
        c.drawString(15, header_y, f"#{self.rank}  {r.name}" if r.name else f"#{self.rank}  {r.enrollment}")

        c.setFont(Fonts.PRIMARY, 9)
        c.setFillColor(CLR_GRAY)
        c.drawRightString(w - 15, header_y, f"{r.enrollment}")

        # ── Info row ──
        info_y = header_y - 18
        c.setFont(Fonts.PRIMARY, 8.5)
        c.setFillColor(CLR_SLATE)
        c.drawString(15, info_y, f"Branch: {r.branch_full or r.branch}  |  Program: {self.program}  |  Semester: {self.semester or 'N/A'}")

        # ── Divider ──
        c.setStrokeColor(CLR_GHOST)
        c.setLineWidth(0.5)
        c.line(15, info_y - 8, w - 15, info_y - 8)

        # ── Subjects Table ──
        subj_y = info_y - 24
        c.setFont(Fonts.PRIMARY_BOLD, 8)
        c.setFillColor(CLR_GRAY)
        c.drawString(15, subj_y, "SUBJECT CODE")
        c.drawString(200, subj_y, "GRADE")

        subj_y -= 4
        for code, grade in r.subjects.items():
            subj_y -= 14
            if subj_y < 70:
                break

            c.setFont(Fonts.PRIMARY, 9)
            c.setFillColor(CLR_NAVY)
            c.drawString(15, subj_y, code[:25])

            is_fail = grade.strip().upper() in {"F", "FAIL", "AB", "ABSENT", "RL"}
            c.setFillColor(CLR_DANGER if is_fail else CLR_SUCCESS_LIGHT)
            c.setFont(Fonts.PRIMARY_BOLD, 9)
            c.drawString(200, subj_y, grade)

        # ── Bottom Summary Bar ──
        bar_h = 40
        c.setFillColor(CLR_SNOW)
        c.rect(0, 0, w, bar_h, fill=1, stroke=0)
        c.setStrokeColor(CLR_GHOST)
        c.line(0, bar_h, w, bar_h)

        # SGPA
        c.setFont(Fonts.PRIMARY, 7.5)
        c.setFillColor(CLR_GRAY)
        c.drawString(15, 25, "SGPA")
        c.setFont(Fonts.PRIMARY_BOLD, 14)
        c.setFillColor(CLR_PRIMARY)
        c.drawString(15, 8, str(r.sgpa or "—"))

        # CGPA
        c.setFont(Fonts.PRIMARY, 7.5)
        c.setFillColor(CLR_GRAY)
        c.drawString(100, 25, "CGPA")
        c.setFont(Fonts.PRIMARY_BOLD, 14)
        c.setFillColor(HexColor('#38BDF8'))
        c.drawString(100, 8, str(r.cgpa or "—"))

        # Result
        c.setFont(Fonts.PRIMARY, 7.5)
        c.setFillColor(CLR_GRAY)
        c.drawString(200, 25, "RESULT")
        c.setFont(Fonts.PRIMARY_BOLD, 14)
        c.setFillColor(result_color)
        c.drawString(200, 8, r.result)

        # Backlogs
        bl_count = len(r.fail_subjects)
        c.setFont(Fonts.PRIMARY, 7.5)
        c.setFillColor(CLR_GRAY)
        c.drawString(320, 25, "BACKLOGS")
        c.setFont(Fonts.PRIMARY_BOLD, 14)
        c.setFillColor(CLR_DANGER if bl_count > 0 else CLR_SUCCESS)
        c.drawString(320, 8, str(bl_count))

        # SGPA indicator bar
        if r.sgpa and r.sgpa > 0:
            bar_x = 410
            bar_w = w - bar_x - 15
            c.setFillColor(CLR_GHOST)
            c.roundRect(bar_x, 10, bar_w, 12, 3, fill=1, stroke=0)
            fill_w = (r.sgpa / 10.0) * bar_w
            c.setFillColor(result_color)
            c.roundRect(bar_x, 10, fill_w, 12, 3, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════

def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render individual student detail pages."""
    records = [r for r in dataset.records if not r.not_found]
    if not records:
        return

    pdf.add_section_header("STUDENT PERFORMANCE DETAILS")
    pdf.add_gradient_divider()
    pdf.add_spacer(4)

    max_students = min(len(records), pdf.config.max_student_pages)
    pdf.add_paragraph(
        f"Individual performance cards for <b>{max_students}</b> student(s). "
        f"Each card shows subject grades, SGPA, CGPA, result status, and backlog count.",
        'Body'
    )
    pdf.add_spacer(8)

    # Sort by SGPA (toppers first)
    sorted_records = sorted(records, key=lambda r: (r.sgpa or 0), reverse=True)

    for i, record in enumerate(sorted_records[:max_students]):
        card = StudentCard(record, i + 1, dataset.program, dataset.semester)
        pdf.add_element(card)
        pdf.add_spacer(10)

        # Page break every 2 students
        if (i + 1) % 2 == 0 and i < max_students - 1:
            pdf.add_page_break()

    pdf.add_page_break()
