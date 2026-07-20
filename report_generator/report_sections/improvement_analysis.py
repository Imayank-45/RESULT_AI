"""
improvement_analysis.py
-----------------------
Most improved and most declined students (requires comparison data).
"""

from __future__ import annotations

from report_generator.pdf_builder import PDFReport
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render Improvement Analysis section."""

    pdf.add_section_header("IMPROVEMENT ANALYSIS")
    pdf.add_gradient_divider()
    pdf.add_spacer(6)

    if not analytics.comparison or not dataset.comparison_records:
        pdf.add_paragraph(
            "Improvement analysis requires comparison data from a previous semester or job. "
            "To enable this section, generate the report with the <b>--compare</b> flag "
            "pointing to a previous result Excel file.",
            'Body'
        )
        pdf.add_spacer(8)
        pdf.add_paragraph(
            "<i>Example: python -m report_generator.generate_report --input current.xlsx --compare previous.xlsx</i>",
            'Small'
        )
        pdf.add_page_break()
        return

    # Build enrollment → SGPA maps
    curr_map = {r.enrollment: r for r in dataset.records if not r.not_found and r.sgpa}
    prev_map = {r.enrollment: r for r in dataset.comparison_records if not r.not_found and r.sgpa}

    common = set(curr_map.keys()) & set(prev_map.keys())

    deltas = []
    for enroll in common:
        curr = curr_map[enroll]
        prev = prev_map[enroll]
        if curr.sgpa and prev.sgpa:
            delta = round(curr.sgpa - prev.sgpa, 2)
            deltas.append((enroll, curr.name, curr.branch, prev.sgpa, curr.sgpa, delta))

    if not deltas:
        pdf.add_paragraph("No common students found between current and previous datasets for comparison.", 'Body')
        pdf.add_page_break()
        return

    # Sort by delta
    improved = sorted(deltas, key=lambda x: x[5], reverse=True)[:15]
    declined = sorted(deltas, key=lambda x: x[5])[:15]

    pdf.add_paragraph(
        f"Comparison based on <b>{len(common)}</b> students present in both current and previous datasets.",
        'Body'
    )
    pdf.add_spacer(10)

    # ── Most Improved ──
    pdf.add_paragraph("<b>MOST IMPROVED STUDENTS</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Enrollment", "Name", "Branch", "Prev SGPA", "Curr SGPA", "Change"]
    rows = []
    for enroll, name, branch, prev_sgpa, curr_sgpa, delta in improved:
        change_str = f"+{delta}" if delta > 0 else str(delta)
        rows.append([enroll, name[:15] if name else "—", branch, str(prev_sgpa), str(curr_sgpa), change_str])
    pdf.add_data_table(headers, rows, col_widths=[80, 90, 55, 70, 70, 60])
    pdf.add_spacer(14)

    # ── Most Declined ──
    pdf.add_paragraph("<b>MOST DECLINED STUDENTS</b>", 'H3')
    pdf.add_spacer(4)

    rows2 = []
    for enroll, name, branch, prev_sgpa, curr_sgpa, delta in declined:
        if delta >= 0:
            continue
        change_str = str(delta)
        rows2.append([enroll, name[:15] if name else "—", branch, str(prev_sgpa), str(curr_sgpa), change_str])
    if rows2:
        pdf.add_data_table(headers, rows2, col_widths=[80, 90, 55, 70, 70, 60])
    else:
        pdf.add_paragraph("No students showed decline in performance.", 'Body')

    pdf.add_page_break()
