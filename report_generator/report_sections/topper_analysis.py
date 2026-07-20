"""
topper_analysis.py
------------------
Top 10 and Top 20 student rank lists with detailed tables.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_PRIMARY, CLR_SUCCESS
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Topper Analysis section."""
    toppers = analytics.toppers
    if not toppers:
        return

    pdf.add_section_header("TOPPER ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    pdf.add_paragraph(
        f"Academic rank list of top-performing students. "
        f"Rankings are based on Semester GPA (SGPA), with CGPA as a tiebreaker.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Top 10 Table ──
    top10 = toppers[:10]
    pdf.add_paragraph("<b>TOP 10 STUDENTS</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Rank", "Enrollment", "Name", "Branch", "SGPA", "CGPA", "Result"]
    rows = []
    for i, t in enumerate(top10, 1):
        medal = "1st" if i == 1 else "2nd" if i == 2 else "3rd" if i == 3 else str(i)
        rows.append([
            medal,
            t.enrollment,
            t.name[:20] if t.name else "—",
            t.branch,
            str(t.sgpa or "—"),
            str(t.cgpa or "—"),
            t.result,
        ])
    pdf.add_data_table(headers, rows, col_widths=[40, 90, 120, 50, 55, 55, 55])
    pdf.add_spacer(14)

    # ── Top 20 Table (if more than 10) ──
    if len(toppers) > 10:
        top20 = toppers[10:20]
        pdf.add_paragraph("<b>RANK 11–20</b>", 'H3')
        pdf.add_spacer(4)

        rows2 = []
        for i, t in enumerate(top20, 11):
            rows2.append([
                str(i),
                t.enrollment,
                t.name[:20] if t.name else "—",
                t.branch,
                str(t.sgpa or "—"),
                str(t.cgpa or "—"),
                t.result,
            ])
        pdf.add_data_table(headers, rows2, col_widths=[40, 90, 120, 50, 55, 55, 55])
        pdf.add_spacer(14)

    # ── Topper SGPA Bar Chart ──
    pdf.add_paragraph("<b>TOP STUDENTS — SGPA VISUALIZATION</b>", 'H3')
    pdf.add_spacer(4)

    top_labels = [f"#{i+1} {t.name.split()[0][:8] if t.name else t.enrollment[-4:]}" for i, t in enumerate(top10)]
    top_values = [t.sgpa or 0 for t in top10]

    chart = chart_renderer.render_bar_chart(
        labels=top_labels, values=top_values,
        title="Top 10 Students — SGPA",
        xlabel="Student", ylabel="SGPA",
        colors=['#22C55E'] * len(top_labels),
        name="topper_sgpa_bar"
    )
    pdf.add_chart(chart, width=440, height=270)

    pdf.add_page_break()
