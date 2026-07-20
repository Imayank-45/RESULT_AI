"""
subject_analysis.py
-------------------
Deep per-subject analysis with difficulty index, grade distribution,
pass rates, and charts.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Subject Analysis section."""
    subjects = analytics.subject_stats
    if not subjects:
        return

    pdf.add_section_header("SUBJECT-WISE ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    pdf.add_paragraph(
        f"Detailed analysis of <b>{len(subjects)}</b> subject(s) evaluated in this semester. "
        f"Each subject is assessed for pass rate, failure rate, average grade, "
        f"difficulty index, and grade distribution.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Subject Summary Table ──
    pdf.add_paragraph("<b>SUBJECT PERFORMANCE SUMMARY</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Subject", "Students", "Pass %", "Fail %", "Avg GP", "Difficulty", "Highest", "Lowest"]
    rows = []
    for ss in sorted(subjects, key=lambda x: x.fail_percentage, reverse=True):
        rows.append([
            ss.code[:12],
            str(ss.total_students),
            f"{ss.pass_percentage}%",
            f"{ss.fail_percentage}%",
            str(ss.average_grade_point),
            str(ss.difficulty_index),
            ss.highest_grade or "—",
            ss.lowest_grade or "—",
        ])
    pdf.add_data_table(headers, rows, col_widths=[75, 55, 55, 55, 55, 60, 60, 60])
    pdf.add_spacer(14)

    # ── Subject Pass Rate Bar Chart ──
    pdf.add_paragraph("<b>SUBJECT-WISE PASS RATE</b>", 'H3')
    pdf.add_spacer(4)

    labels = [ss.code[:10] for ss in subjects]
    values = [ss.pass_percentage for ss in subjects]
    colors = ['#22C55E' if v >= 80 else '#F59E0B' if v >= 50 else '#EF4444' for v in values]

    chart = chart_renderer.render_bar_chart(
        labels=labels, values=values,
        title="Subject-wise Pass Rate (%)",
        xlabel="Subject", ylabel="Pass Rate (%)",
        colors=colors, name="subject_pass_rate"
    )
    pdf.add_chart(chart, width=440, height=260)
    pdf.add_spacer(10)

    # ── Difficulty Index Chart ──
    pdf.add_page_break()
    pdf.add_paragraph("<b>SUBJECT DIFFICULTY INDEX</b>", 'H3')
    pdf.add_spacer(4)
    pdf.add_paragraph(
        "The Difficulty Index ranges from 0.0 (easiest) to 1.0 (hardest), "
        "calculated based on average grade points. Higher values indicate more challenging subjects.",
        'Small'
    )
    pdf.add_spacer(4)

    diff_labels = [ss.code[:10] for ss in sorted(subjects, key=lambda x: x.difficulty_index, reverse=True)]
    diff_values = [ss.difficulty_index for ss in sorted(subjects, key=lambda x: x.difficulty_index, reverse=True)]
    diff_colors = ['#EF4444' if v > 0.6 else '#F59E0B' if v > 0.4 else '#22C55E' for v in diff_values]

    chart2 = chart_renderer.render_bar_chart(
        labels=diff_labels, values=diff_values,
        title="Subject Difficulty Index",
        xlabel="Subject", ylabel="Difficulty (0–1)",
        colors=diff_colors, horizontal=True,
        name="subject_difficulty"
    )
    pdf.add_chart(chart2, width=430, height=260)
    pdf.add_spacer(14)

    # ── Individual Subject Details ──
    pdf.add_paragraph("<b>DETAILED SUBJECT BREAKDOWN</b>", 'H3')
    pdf.add_spacer(4)

    for i, ss in enumerate(subjects):
        detail = (
            f"<b>{ss.code}</b>: {ss.total_students} students, "
            f"Pass Rate: {ss.pass_percentage}%, "
            f"Fail Rate: {ss.fail_percentage}%, "
            f"Avg Grade Point: {ss.average_grade_point}, "
            f"Failed: {ss.failed}"
        )
        if ss.grade_distribution:
            grades_str = ", ".join(f"{g}: {c}" for g, c in sorted(ss.grade_distribution.items()))
            detail += f" — Grades: [{grades_str}]"
        pdf.add_paragraph(f"• {detail}", 'Body')

    # ── Most Failed / Highest Achievement ──
    pdf.add_spacer(10)
    if analytics.most_failed_subject:
        pdf.add_paragraph(
            f"<b>Most Failed Subject:</b> {analytics.most_failed_subject}",
            'BodyBold'
        )

    easiest = min(subjects, key=lambda x: x.difficulty_index) if subjects else None
    if easiest:
        pdf.add_paragraph(
            f"<b>Easiest Subject:</b> {easiest.code} (Difficulty Index: {easiest.difficulty_index})",
            'BodyBold'
        )

    pdf.add_page_break()
