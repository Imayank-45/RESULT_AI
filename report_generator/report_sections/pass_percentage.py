"""
pass_percentage.py
------------------
Pass percentage analysis with gauge chart and trend data.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Pass Percentage Analysis section."""
    ov = analytics.overall

    pdf.add_section_header("PASS PERCENTAGE ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    pdf.add_paragraph(
        f"Overall pass rate analysis showing the proportion of students who cleared "
        f"all subjects versus those with one or more failures.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Gauge Chart ──
    pdf.add_paragraph("<b>OVERALL PASS RATE GAUGE</b>", 'H3')
    pdf.add_spacer(4)

    chart1 = chart_renderer.render_gauge_chart(
        value=ov.pass_percentage,
        max_val=100.0,
        title="Overall Pass Percentage",
        label="Pass Rate",
        name="pass_gauge"
    )
    pdf.add_chart(chart1, width=300, height=240)
    pdf.add_spacer(12)

    # ── Department-wise Pass Rate ──
    if analytics.branch_stats:
        pdf.add_paragraph("<b>DEPARTMENT-WISE PASS RATE</b>", 'H3')
        pdf.add_spacer(4)

        headers = ["Department", "Total", "Passed", "Failed", "Pass %"]
        rows = []
        for bs in sorted(analytics.branch_stats, key=lambda x: x.pass_percentage, reverse=True):
            rows.append([
                bs.branch_name[:25],
                str(bs.total),
                str(bs.passed),
                str(bs.failed),
                f"{bs.pass_percentage}%"
            ])
        pdf.add_data_table(headers, rows, col_widths=[160, 70, 70, 70, 80])
        pdf.add_spacer(14)

        # Bar chart
        labels = [bs.branch_code for bs in analytics.branch_stats]
        values = [bs.pass_percentage for bs in analytics.branch_stats]
        colors = ['#22C55E' if v >= 80 else '#F59E0B' if v >= 50 else '#EF4444' for v in values]

        chart2 = chart_renderer.render_bar_chart(
            labels=labels, values=values,
            title="Department-wise Pass Rate (%)",
            xlabel="Department", ylabel="Pass Rate (%)",
            colors=colors, name="pass_dept_bar"
        )
        pdf.add_chart(chart2, width=430, height=260)

    # ── Comparison trend (if available) ──
    if analytics.comparison:
        pdf.add_spacer(14)
        pdf.add_paragraph("<b>PASS RATE TREND</b>", 'H3')
        pdf.add_spacer(4)

        comp = analytics.comparison
        chart3 = chart_renderer.render_bar_chart(
            labels=["Previous", "Current"],
            values=[comp['prev_pass_pct'], comp['curr_pass_pct']],
            title="Pass Rate — Previous vs Current",
            ylabel="Pass Rate (%)",
            colors=['#64748B', '#4F46E5'],
            name="pass_trend"
        )
        pdf.add_chart(chart3, width=350, height=240)

    pdf.add_page_break()
