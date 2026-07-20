"""
risk_analysis.py
----------------
Risk stratification: at-risk students, near-distinction, multi-backlog.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_DANGER, CLR_WARNING, CLR_SUCCESS
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Risk Analysis section."""

    pdf.add_section_header("RISK ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    at_risk = analytics.students_at_risk
    near_dist = analytics.students_near_distinction
    multi_bl = analytics.students_multi_backlog

    pdf.add_paragraph(
        f"Academic risk stratification identifying students who need attention. "
        f"<b>{len(at_risk)}</b> at-risk, <b>{len(near_dist)}</b> near-distinction, "
        f"<b>{len(multi_bl)}</b> with multiple backlogs.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Risk Summary Pie ──
    chart1 = chart_renderer.render_pie_chart(
        labels=["At Risk", "Near Distinction", "Multiple Backlogs",
                "Safe"],
        values=[len(at_risk), len(near_dist), len(multi_bl),
                max(0, analytics.overall.total_students - len(at_risk) - len(near_dist))],
        title="Student Risk Distribution",
        colors=['#EF4444', '#F59E0B', '#E11D4C', '#22C55E'],
        name="risk_pie"
    )
    pdf.add_chart(chart1, width=350, height=280)
    pdf.add_spacer(10)

    # ── Students At Risk (SGPA < 5.0 or FAIL) ──
    if at_risk:
        pdf.add_paragraph("<b>STUDENTS AT RISK</b>  (SGPA &lt; 5.0 or FAIL status)", 'H3')
        pdf.add_spacer(4)

        headers = ["Enrollment", "Name", "Branch", "SGPA", "CGPA", "Backlogs"]
        rows = []
        for s in at_risk[:30]:
            rows.append([
                s.enrollment, s.name[:18] if s.name else "—",
                s.branch[:15], str(s.sgpa), str(s.cgpa), str(s.backlog_count)
            ])
        pdf.add_data_table(headers, rows, col_widths=[85, 100, 90, 60, 60, 60])
        pdf.add_spacer(14)

    # ── Near Distinction (SGPA 7.5–8.5) ──
    if near_dist:
        pdf.add_paragraph("<b>STUDENTS NEAR DISTINCTION</b>  (SGPA 7.5–8.5)", 'H3')
        pdf.add_spacer(4)

        headers2 = ["Enrollment", "Name", "Branch", "SGPA", "CGPA"]
        rows2 = []
        for s in near_dist[:20]:
            rows2.append([
                s.enrollment, s.name[:18] if s.name else "—",
                s.branch[:15], str(s.sgpa), str(s.cgpa)
            ])
        pdf.add_data_table(headers2, rows2, col_widths=[95, 120, 110, 70, 70])
        pdf.add_spacer(14)

    # ── Multiple Backlogs ──
    if multi_bl:
        pdf.add_page_break()
        pdf.add_paragraph("<b>STUDENTS WITH MULTIPLE BACKLOGS</b>  (2+ subjects)", 'H3')
        pdf.add_spacer(4)

        headers3 = ["Enrollment", "Name", "Branch", "SGPA", "Backlogs"]
        rows3 = []
        for s in multi_bl[:30]:
            rows3.append([
                s.enrollment, s.name[:18] if s.name else "—",
                s.branch[:15], str(s.sgpa), str(s.backlog_count)
            ])
        pdf.add_data_table(headers3, rows3, col_widths=[95, 120, 110, 70, 70])

    pdf.add_page_break()
