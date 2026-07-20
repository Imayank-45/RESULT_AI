"""
heatmaps.py
-----------
Branch × Subject performance heatmaps and failure heatmap.
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult
from report_generator import chart_renderer


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Heatmaps section."""
    heatmap_data = analytics.heatmap_data
    if not heatmap_data:
        return

    pdf.add_section_header("PERFORMANCE HEATMAPS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    pdf.add_paragraph(
        "Visual heatmaps showing performance intensity across branches and subjects. "
        "Warmer colors (red/orange) indicate weaker performance; cooler colors (green) indicate stronger results. "
        "Grade points range from 0 (Fail) to 10 (Outstanding).",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Branch × Subject Heatmap ──
    pdf.add_paragraph("<b>BRANCH × SUBJECT PERFORMANCE HEATMAP</b>", 'H3')
    pdf.add_spacer(4)

    chart1 = chart_renderer.render_heatmap(
        data=heatmap_data,
        title="Average Grade Points — Branch vs Subject",
        name="heatmap_branch_subject"
    )
    pdf.add_chart(chart1, width=460, height=280)
    pdf.add_spacer(14)

    # ── Failure Intensity Heatmap (reconstruct from subject stats) ──
    failure_data = {}
    for bs in analytics.branch_stats:
        failure_data[bs.branch_code] = {}

    # Build branch × subject failure rate matrix
    from collections import defaultdict
    branch_subject_fails = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    for r in dataset.records:
        if r.not_found:
            continue
        for code, grade in r.subjects.items():
            branch_subject_fails[r.branch][code][1] += 1
            if grade.strip().upper() in {"F", "FAIL", "AB", "ABSENT", "RL"}:
                branch_subject_fails[r.branch][code][0] += 1

    fail_heatmap = {}
    for branch, subjects in branch_subject_fails.items():
        fail_heatmap[branch] = {}
        for subj, (fails, total) in subjects.items():
            fail_heatmap[branch][subj] = round(fails / max(total, 1) * 10, 1)  # Scale to 0-10

    if fail_heatmap:
        pdf.add_page_break()
        pdf.add_paragraph("<b>FAILURE INTENSITY HEATMAP</b>", 'H3')
        pdf.add_spacer(4)
        pdf.add_paragraph(
            "Higher values (red) indicate higher failure rates. Scale: 0 = No Failures, 10 = 100% Failure.",
            'Small'
        )
        pdf.add_spacer(4)

        chart2 = chart_renderer.render_heatmap(
            data=fail_heatmap,
            title="Failure Intensity — Branch vs Subject",
            name="heatmap_failure"
        )
        pdf.add_chart(chart2, width=460, height=280)

    pdf.add_page_break()
