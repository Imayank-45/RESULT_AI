"""
overall_statistics.py
---------------------
Comprehensive overall statistics page with full metrics table
and SGPA distribution chart.
"""

from __future__ import annotations

from report_generator.pdf_builder import (
    PDFReport, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER, CLR_WARNING
)
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render the Overall Statistics section."""
    ov = analytics.overall

    pdf.add_section_header("OVERALL STATISTICS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    pdf.add_paragraph(
        f"Complete statistical overview of <b>{ov.total_students}</b> students "
        f"across <b>{len(analytics.branch_stats)}</b> department(s) and "
        f"<b>{len(analytics.subject_stats)}</b> subject(s).",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Result Breakdown Table ──
    pdf.add_paragraph("<b>RESULT BREAKDOWN</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Category", "Count", "Percentage"]
    rows = [
        ["Total Students", str(ov.total_students), "100%"],
        ["Passed", str(ov.passed), f"{ov.pass_percentage}%"],
        ["Failed", str(ov.failed), f"{ov.fail_percentage}%"],
        ["Unknown/Pending", str(ov.unknown), f"{round(ov.unknown / max(ov.total_students, 1) * 100, 1)}%"],
    ]
    pdf.add_data_table(headers, rows, col_widths=[200, 150, 145])
    pdf.add_spacer(14)

    # ── SGPA Statistics ──
    pdf.add_paragraph("<b>SGPA STATISTICS</b>", 'H3')
    pdf.add_spacer(4)

    headers2 = ["Statistic", "SGPA", "CGPA"]
    rows2 = [
        ["Highest", str(ov.highest_sgpa), str(ov.highest_cgpa)],
        ["Lowest", str(ov.lowest_sgpa), str(ov.lowest_cgpa)],
        ["Average (Mean)", str(ov.average_sgpa), str(ov.average_cgpa)],
        ["Median", str(ov.median_sgpa), str(ov.median_cgpa)],
        ["Std. Deviation", str(ov.std_dev_sgpa), "—"],
    ]
    pdf.add_data_table(headers2, rows2, col_widths=[200, 148, 147])
    pdf.add_spacer(14)

    # ── SGPA Distribution Chart ──
    pdf.add_paragraph("<b>SGPA DISTRIBUTION</b>", 'H3')
    pdf.add_spacer(4)

    sd = analytics.sgpa_distribution
    if sd and any(v > 0 for v in sd.values()):
        chart_path = chart_renderer.render_bar_chart(
            labels=list(sd.keys()),
            values=list(sd.values()),
            title="SGPA Distribution Across Students",
            xlabel="SGPA Range",
            ylabel="Number of Students",
            name="overall_sgpa_dist"
        )
        pdf.add_chart(chart_path, width=430, height=260)
    pdf.add_spacer(8)

    # ── Pass/Fail Pie Chart ──
    if ov.passed + ov.failed > 0:
        chart_path2 = chart_renderer.render_pie_chart(
            labels=["Passed", "Failed", "Unknown"],
            values=[ov.passed, ov.failed, ov.unknown],
            title="Result Distribution",
            colors=['#22C55E', '#EF4444', '#64748B'],
            name="overall_result_pie"
        )
        pdf.add_chart(chart_path2, width=350, height=280)

    pdf.add_page_break()
