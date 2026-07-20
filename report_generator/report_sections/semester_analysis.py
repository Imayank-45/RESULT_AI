"""
semester_analysis.py
--------------------
Semester-wise performance analysis.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Semester Analysis section."""
    ov = analytics.overall

    pdf.add_section_header("SEMESTER ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    sem = dataset.semester or "Current"
    pdf.add_paragraph(
        f"Performance analysis for <b>Semester {sem}</b> of the <b>{dataset.program}</b> program. "
        f"This section provides a snapshot of the semester's academic outcomes.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Semester Overview ──
    pdf.add_paragraph("<b>SEMESTER PERFORMANCE OVERVIEW</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Metric", "Value"]
    rows = [
        ["Semester", f"Semester {sem}"],
        ["Program", dataset.program],
        ["Total Students", str(ov.total_students)],
        ["Pass Count", str(ov.passed)],
        ["Fail Count", str(ov.failed)],
        ["Pass Percentage", f"{ov.pass_percentage}%"],
        ["Average SGPA", str(ov.average_sgpa)],
        ["Average CGPA", str(ov.average_cgpa)],
        ["Highest SGPA", str(ov.highest_sgpa)],
        ["Lowest SGPA", str(ov.lowest_sgpa)],
        ["Number of Subjects", str(len(analytics.subject_stats))],
        ["Departments", str(len(analytics.branch_stats))],
    ]
    pdf.add_data_table(headers, rows, col_widths=[250, 245])
    pdf.add_spacer(14)

    # ── Per-Branch Semester Performance ──
    if analytics.branch_stats:
        pdf.add_paragraph("<b>DEPARTMENT-WISE SEMESTER RESULTS</b>", 'H3')
        pdf.add_spacer(4)

        headers2 = ["Department", "Students", "Pass %", "Avg SGPA", "Topper"]
        rows2 = []
        for bs in analytics.branch_stats:
            rows2.append([
                bs.branch_name[:25],
                str(bs.total),
                f"{bs.pass_percentage}%",
                str(bs.average_sgpa),
                bs.topper_name[:18] if bs.topper_name else "—",
            ])
        pdf.add_data_table(headers2, rows2, col_widths=[140, 70, 70, 80, 135])

    pdf.add_spacer(12)
    pdf.add_paragraph(
        "<i>Note: Multi-semester trend analysis requires comparison data from previous semesters. "
        "Use the --compare flag with a previous semester's Excel file to enable trend charts.</i>",
        'Small'
    )

    pdf.add_page_break()
