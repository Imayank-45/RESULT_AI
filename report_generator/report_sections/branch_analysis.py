"""
branch_analysis.py
------------------
Branch-wise comparative analysis with tables, bar charts, and radar chart.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Branch Analysis section."""
    branches = analytics.branch_stats
    if not branches:
        return

    pdf.add_section_header("BRANCH-WISE ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    pdf.add_paragraph(
        f"Comparative performance analysis across <b>{len(branches)}</b> academic department(s). "
        f"This section evaluates each branch based on average SGPA, pass rate, failure rate, "
        f"and backlog distribution.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Comparison Table ──
    pdf.add_paragraph("<b>DEPARTMENT COMPARISON TABLE</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Branch", "Students", "Pass %", "Fail %", "Avg SGPA", "Avg CGPA", "Backlogs", "Topper"]
    rows = []
    for bs in sorted(branches, key=lambda x: x.average_sgpa, reverse=True):
        rows.append([
            bs.branch_code,
            str(bs.total),
            f"{bs.pass_percentage}%",
            f"{bs.fail_percentage}%",
            str(bs.average_sgpa),
            str(bs.average_cgpa),
            str(bs.backlog_count),
            bs.topper_name[:15] if bs.topper_name else "—"
        ])

    pdf.add_data_table(headers, rows, col_widths=[50, 55, 55, 55, 65, 65, 60, 90])
    pdf.add_spacer(14)

    # ── Average SGPA Bar Chart ──
    if len(branches) >= 2:
        pdf.add_paragraph("<b>AVERAGE SGPA BY DEPARTMENT</b>", 'H3')
        pdf.add_spacer(4)

        labels = [bs.branch_code for bs in branches]
        values = [bs.average_sgpa for bs in branches]
        chart = chart_renderer.render_bar_chart(
            labels=labels, values=values,
            title="Average SGPA — Department Comparison",
            xlabel="Department", ylabel="Average SGPA",
            name="branch_sgpa_bar"
        )
        pdf.add_chart(chart, width=430, height=260)
        pdf.add_spacer(10)

    # ── Pass Rate Comparison ──
    if len(branches) >= 2:
        pdf.add_paragraph("<b>PASS RATE COMPARISON</b>", 'H3')
        pdf.add_spacer(4)

        labels_p = [bs.branch_code for bs in branches]
        pass_vals = [bs.pass_percentage for bs in branches]
        fail_vals = [bs.fail_percentage for bs in branches]

        chart2 = chart_renderer.render_stacked_bar(
            categories=labels_p,
            series={"Pass %": pass_vals, "Fail %": fail_vals},
            title="Pass vs Fail Rate by Department",
            ylabel="Percentage (%)",
            name="branch_pass_fail_stacked"
        )
        pdf.add_chart(chart2, width=430, height=260)
        pdf.add_spacer(10)

    # ── Radar Chart (if multiple branches) ──
    if len(branches) >= 3:
        pdf.add_page_break()
        pdf.add_paragraph("<b>MULTI-DIMENSIONAL COMPARISON</b>", 'H3')
        pdf.add_spacer(4)

        radar_labels = [bs.branch_code for bs in branches[:8]]  # Cap at 8
        radar_values = [bs.average_sgpa for bs in branches[:8]]

        chart3 = chart_renderer.render_radar_chart(
            labels=radar_labels, values=radar_values,
            title="Department Performance Radar",
            name="branch_radar"
        )
        pdf.add_chart(chart3, width=340, height=340)

    pdf.add_page_break()
