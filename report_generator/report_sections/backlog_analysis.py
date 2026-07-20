"""
backlog_analysis.py
-------------------
Backlog analysis: department-wise, subject-wise, and student-wise breakdown.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_DANGER
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Backlog Analysis section."""

    pdf.add_section_header("BACKLOG ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    # Count total backlogs
    total_backlogs = sum(analytics.backlog_by_subject.values())
    students_with_bl = sum(1 for r in dataset.records if not r.not_found and len(r.fail_subjects) > 0)

    pdf.add_paragraph(
        f"Analysis of <b>{total_backlogs}</b> total backlog instances across "
        f"<b>{students_with_bl}</b> student(s). Backlogs include F, Fail, AB, Absent, and RL grades.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Department-wise Backlogs ──
    if analytics.backlog_by_dept:
        pdf.add_paragraph("<b>DEPARTMENT-WISE BACKLOG DISTRIBUTION</b>", 'H3')
        pdf.add_spacer(4)

        headers = ["Department", "Total Backlogs"]
        rows = [[dept, str(count)] for dept, count in
                sorted(analytics.backlog_by_dept.items(), key=lambda x: x[1], reverse=True)]
        pdf.add_data_table(headers, rows, col_widths=[300, 195])
        pdf.add_spacer(14)

        # Chart
        labels = [d[:12] for d, _ in sorted(analytics.backlog_by_dept.items(), key=lambda x: x[1], reverse=True)]
        values = [c for _, c in sorted(analytics.backlog_by_dept.items(), key=lambda x: x[1], reverse=True)]
        chart1 = chart_renderer.render_bar_chart(
            labels=labels, values=values,
            title="Backlogs by Department",
            xlabel="Department", ylabel="Backlog Count",
            colors=['#EF4444'] * len(labels),
            name="backlog_dept"
        )
        pdf.add_chart(chart1, width=430, height=250)
        pdf.add_spacer(10)

    # ── Subject-wise Backlogs ──
    if analytics.backlog_by_subject:
        pdf.add_page_break()
        pdf.add_paragraph("<b>SUBJECT-WISE BACKLOG DISTRIBUTION</b>", 'H3')
        pdf.add_spacer(4)

        headers2 = ["Subject Code", "Failure Count"]
        rows2 = [[subj, str(count)] for subj, count in
                  sorted(analytics.backlog_by_subject.items(), key=lambda x: x[1], reverse=True)]
        pdf.add_data_table(headers2, rows2, col_widths=[300, 195])
        pdf.add_spacer(14)

        # Chart
        labels2 = [s[:10] for s, _ in sorted(analytics.backlog_by_subject.items(), key=lambda x: x[1], reverse=True)[:15]]
        values2 = [c for _, c in sorted(analytics.backlog_by_subject.items(), key=lambda x: x[1], reverse=True)[:15]]
        chart2 = chart_renderer.render_bar_chart(
            labels=labels2, values=values2,
            title="Most Failed Subjects",
            xlabel="Subject", ylabel="Failures",
            colors=['#E11D4C'] * len(labels2),
            horizontal=True,
            name="backlog_subject"
        )
        pdf.add_chart(chart2, width=430, height=260)
        pdf.add_spacer(10)

    # ── Student-wise Backlog List ──
    students_with_backlogs = [r for r in dataset.records if not r.not_found and len(r.fail_subjects) > 0]
    if students_with_backlogs:
        pdf.add_paragraph("<b>STUDENTS WITH BACKLOGS</b>", 'H3')
        pdf.add_spacer(4)

        headers3 = ["Enrollment", "Name", "Branch", "SGPA", "Backlogs", "Failed Subjects"]
        rows3 = []
        for r in sorted(students_with_backlogs, key=lambda x: len(x.fail_subjects), reverse=True)[:50]:
            fail_str = ", ".join(s.split("-")[0].strip() if "-" in s else s for s in r.fail_subjects[:5])
            rows3.append([
                r.enrollment,
                r.name[:15] if r.name else "—",
                r.branch,
                str(r.sgpa or "—"),
                str(len(r.fail_subjects)),
                fail_str[:25],
            ])
        pdf.add_data_table(headers3, rows3, col_widths=[80, 80, 50, 55, 55, 175])

    pdf.add_page_break()
