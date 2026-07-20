"""
grade_distribution.py
---------------------
Grade distribution charts: pie, bar, histogram, stacked.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_PRIMARY
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


GRADE_COLORS = {
    'O':  '#059669', 'A+': '#22C55E', 'A': '#38BDF8', 'B+': '#6366F1',
    'B':  '#7C3AED', 'C':  '#F59E0B', 'P': '#EC7424', 'F':  '#EF4444',
    'AB': '#94A3B8', 'ABSENT': '#94A3B8', 'RL': '#64748B',
}


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Grade Distribution section."""
    gd = analytics.grade_distribution
    if not gd:
        return

    pdf.add_section_header("GRADE DISTRIBUTION")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    total = sum(gd.values())
    pdf.add_paragraph(
        f"Distribution analysis of <b>{total}</b> total grades awarded across all subjects and students.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Grade Distribution Table ──
    pdf.add_paragraph("<b>GRADE FREQUENCY TABLE</b>", 'H3')
    pdf.add_spacer(4)

    grade_order = ['O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'AB', 'ABSENT', 'RL']
    ordered = [(g, gd.get(g, 0)) for g in grade_order if g in gd]
    # Add any grades not in standard order
    for g, c in sorted(gd.items()):
        if g not in grade_order:
            ordered.append((g, c))

    headers = ["Grade", "Count", "Percentage", "Performance Level"]
    rows = []
    levels = {
        'O': 'Outstanding', 'A+': 'Excellent', 'A': 'Very Good',
        'B+': 'Good', 'B': 'Above Average', 'C': 'Average',
        'P': 'Pass', 'F': 'Fail', 'AB': 'Absent', 'ABSENT': 'Absent', 'RL': 'Reappear'
    }
    for grade, count in ordered:
        pct = round(count / total * 100, 1) if total > 0 else 0
        rows.append([grade, str(count), f"{pct}%", levels.get(grade, grade)])
    pdf.add_data_table(headers, rows, col_widths=[80, 100, 100, 215])
    pdf.add_spacer(14)

    # ── Pie Chart ──
    pdf.add_paragraph("<b>GRADE DISTRIBUTION — DONUT CHART</b>", 'H3')
    pdf.add_spacer(4)

    labels = [g for g, _ in ordered if _ > 0]
    values = [c for _, c in ordered if c > 0]
    colors = [GRADE_COLORS.get(g, '#64748B') for g in labels]

    chart1 = chart_renderer.render_pie_chart(
        labels=labels, values=values,
        title="Grade Distribution",
        colors=colors, name="grade_pie"
    )
    pdf.add_chart(chart1, width=380, height=300)
    pdf.add_spacer(10)

    # ── Bar Chart ──
    pdf.add_page_break()
    pdf.add_paragraph("<b>GRADE DISTRIBUTION — BAR CHART</b>", 'H3')
    pdf.add_spacer(4)

    chart2 = chart_renderer.render_bar_chart(
        labels=labels, values=values,
        title="Grade Frequency Distribution",
        xlabel="Grade", ylabel="Count",
        colors=colors, name="grade_bar"
    )
    pdf.add_chart(chart2, width=440, height=270)
    pdf.add_spacer(14)

    # ── SGPA Histogram ──
    pdf.add_paragraph("<b>SGPA FREQUENCY HISTOGRAM</b>", 'H3')
    pdf.add_spacer(4)

    sgpa_values = [r.sgpa for r in dataset.records if not r.not_found and r.sgpa is not None and r.sgpa > 0]
    if sgpa_values:
        chart3 = chart_renderer.render_histogram(
            values=sgpa_values,
            title="SGPA Distribution — Histogram",
            xlabel="SGPA", ylabel="Number of Students",
            bins=min(len(sgpa_values), 15),
            name="sgpa_histogram"
        )
        pdf.add_chart(chart3, width=430, height=260)

    pdf.add_page_break()
