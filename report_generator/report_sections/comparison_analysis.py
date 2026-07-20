"""
comparison_analysis.py
----------------------
Side-by-side comparison: Previous vs Current job/semester.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Comparison Analysis section."""

    pdf.add_section_header("COMPARISON ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    if not analytics.comparison:
        pdf.add_paragraph(
            "Comparison analysis is available when a previous dataset is provided for reference. "
            "Use the <b>--compare</b> flag to specify a previous result Excel file.",
            'Body'
        )
        pdf.add_spacer(8)
        pdf.add_paragraph(
            "<i>Example: python -m report_generator.generate_report --input current.xlsx --compare previous.xlsx</i>",
            'Small'
        )
        pdf.add_page_break()
        return

    comp = analytics.comparison

    pdf.add_paragraph(
        f"Side-by-side comparison between the current evaluation and a previous reference dataset. "
        f"Previous dataset had <b>{comp['prev_total']}</b> students; "
        f"current dataset has <b>{comp['curr_total']}</b> students.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Overall Comparison Table ──
    pdf.add_paragraph("<b>OVERALL COMPARISON</b>", 'H3')
    pdf.add_spacer(4)

    def delta_str(d):
        if d > 0:
            return f"+{d}"
        return str(d)

    headers = ["Metric", "Previous", "Current", "Change"]
    rows = [
        ["Total Students", str(comp['prev_total']), str(comp['curr_total']),
         delta_str(comp['curr_total'] - comp['prev_total'])],
        ["Pass Percentage", f"{comp['prev_pass_pct']}%", f"{comp['curr_pass_pct']}%",
         delta_str(comp['pass_pct_delta']) + "%"],
        ["Average SGPA", str(comp['prev_avg_sgpa']), str(comp['curr_avg_sgpa']),
         delta_str(comp['sgpa_delta'])],
    ]
    pdf.add_data_table(headers, rows, col_widths=[140, 110, 110, 100])
    pdf.add_spacer(14)

    # ── Comparison Bar Chart ──
    pdf.add_paragraph("<b>VISUAL COMPARISON</b>", 'H3')
    pdf.add_spacer(4)

    chart1 = chart_renderer.render_bar_chart(
        labels=["Avg SGPA (Prev)", "Avg SGPA (Curr)", "Pass % (Prev)", "Pass % (Curr)"],
        values=[comp['prev_avg_sgpa'], comp['curr_avg_sgpa'],
                comp['prev_pass_pct'], comp['curr_pass_pct']],
        title="Previous vs Current — Key Metrics",
        ylabel="Value",
        colors=['#94A3B8', '#4F46E5', '#94A3B8', '#22C55E'],
        name="comparison_bar"
    )
    pdf.add_chart(chart1, width=430, height=260)
    pdf.add_spacer(14)

    # ── Branch-wise Delta ──
    branch_deltas = comp.get("branch_deltas", {})
    if branch_deltas:
        pdf.add_paragraph("<b>DEPARTMENT-WISE CHANGES</b>", 'H3')
        pdf.add_spacer(4)

        headers2 = ["Department", "SGPA Change", "Pass % Change"]
        rows2 = []
        for code, delta in sorted(branch_deltas.items()):
            rows2.append([
                delta.get("name", code),
                delta_str(delta.get("sgpa_delta", 0)),
                delta_str(delta.get("pass_pct_delta", 0)) + "%",
            ])
        pdf.add_data_table(headers2, rows2, col_widths=[220, 120, 120])

    pdf.add_page_break()
