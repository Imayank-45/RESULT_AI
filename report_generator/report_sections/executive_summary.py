"""
executive_summary.py
--------------------
AI-written executive summary with overall performance metrics,
key findings, and high-level observations.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.colors import HexColor

from report_generator.pdf_builder import (
    PDFReport, CLR_NAVY, CLR_PRIMARY, CLR_SUCCESS, CLR_DANGER, CLR_WARNING,
    CLR_SLATE, CLR_GRAY, CLR_GHOST, CLR_SNOW, GradientDivider, MetricCard
)
from report_generator.data_loader import ReportDataset
from report_generator.analytics_engine import AnalyticsResult


def render(pdf: PDFReport, dataset: ReportDataset, analytics: AnalyticsResult):
    """Render the Executive Summary section."""
    ov = analytics.overall

    pdf.add_section_header("EXECUTIVE SUMMARY")
    pdf.add_gradient_divider()
    pdf.add_spacer(8)

    # ── Opening paragraph ──
    summary_text = (
        f"This report presents a comprehensive analysis of academic performance for "
        f"<b>{ov.total_students}</b> students enrolled in the <b>{dataset.program}</b> program"
    )
    if dataset.semester:
        summary_text += f", Semester <b>{dataset.semester}</b>"
    summary_text += (
        f" at <b>{dataset.college_name}</b>. "
        f"The analysis covers overall statistics, branch-wise comparisons, subject-level insights, "
        f"grade distributions, risk assessments, and AI-generated recommendations for academic improvement."
    )
    pdf.add_paragraph(summary_text, 'Body')
    pdf.add_spacer(12)

    # ── Key Metric Cards ──
    pdf.add_paragraph("<b>KEY PERFORMANCE INDICATORS</b>", 'H3')
    pdf.add_spacer(6)

    metrics = [
        ("Total Students", str(ov.total_students), CLR_PRIMARY),
        ("Pass Rate", f"{ov.pass_percentage}%", CLR_SUCCESS),
        ("Fail Rate", f"{ov.fail_percentage}%", CLR_DANGER),
        ("Avg SGPA", str(ov.average_sgpa), HexColor('#6366F1')),
    ]
    pdf.add_metric_row(metrics)
    pdf.add_spacer(12)

    metrics2 = [
        ("Avg CGPA", str(ov.average_cgpa), HexColor('#38BDF8')),
        ("Highest SGPA", str(ov.highest_sgpa), CLR_SUCCESS),
        ("Lowest SGPA", str(ov.lowest_sgpa), CLR_DANGER),
        ("Median SGPA", str(ov.median_sgpa), CLR_WARNING),
    ]
    pdf.add_metric_row(metrics2)
    pdf.add_spacer(16)

    # ── Key Findings ──
    pdf.add_paragraph("<b>KEY FINDINGS</b>", 'H3')
    pdf.add_spacer(4)

    findings = []

    # Pass/Fail status
    if ov.pass_percentage >= 90:
        findings.append(f"<b>Excellent batch performance</b> — {ov.pass_percentage}% of students passed all subjects, indicating strong academic standards.")
    elif ov.pass_percentage >= 70:
        findings.append(f"<b>Good academic outcome</b> — {ov.pass_percentage}% pass rate with {ov.failed} students requiring support.")
    elif ov.pass_percentage >= 50:
        findings.append(f"<b>Moderate performance</b> — {ov.pass_percentage}% pass rate indicates need for academic intervention programs.")
    else:
        findings.append(f"<b>Critical attention required</b> — only {ov.pass_percentage}% pass rate, with {ov.failed} students failing one or more subjects.")

    # Topper
    if ov.topper_name:
        findings.append(f"<b>Batch Topper:</b> {ov.topper_name} ({ov.topper_enrollment}) achieved the highest SGPA of {ov.topper_sgpa}.")

    # SGPA analysis
    if ov.average_sgpa > 7.5:
        findings.append(f"The average SGPA of <b>{ov.average_sgpa}</b> reflects strong overall academic performance.")
    elif ov.average_sgpa > 6.0:
        findings.append(f"The average SGPA of <b>{ov.average_sgpa}</b> is satisfactory but has scope for improvement.")
    elif ov.average_sgpa > 0:
        findings.append(f"The average SGPA of <b>{ov.average_sgpa}</b> is below expected levels and requires immediate attention.")

    # Best/Weakest department
    if analytics.best_branch:
        findings.append(f"<b>Best performing department:</b> {analytics.best_branch}.")
    if analytics.weakest_branch and analytics.weakest_branch != analytics.best_branch:
        findings.append(f"<b>Department needing support:</b> {analytics.weakest_branch}.")

    # Most failed subject
    if analytics.most_failed_subject:
        findings.append(f"<b>Most challenging subject:</b> {analytics.most_failed_subject} recorded the highest failure rate.")

    # Risk
    at_risk = len(analytics.students_at_risk)
    if at_risk > 0:
        findings.append(f"<b>{at_risk} student(s)</b> identified as academically at-risk and require targeted intervention.")

    for finding in findings:
        pdf.add_paragraph(f"• {finding}", 'Body')

    pdf.add_spacer(12)

    # ── Summary Statistics Table ──
    pdf.add_paragraph("<b>PERFORMANCE SNAPSHOT</b>", 'H3')
    pdf.add_spacer(4)

    headers = ["Metric", "Value"]
    rows = [
        ["Total Students Evaluated", str(ov.total_students)],
        ["Students Passed", f"{ov.passed} ({ov.pass_percentage}%)"],
        ["Students Failed", f"{ov.failed} ({ov.fail_percentage}%)"],
        ["Average SGPA", str(ov.average_sgpa)],
        ["Median SGPA", str(ov.median_sgpa)],
        ["Standard Deviation", str(ov.std_dev_sgpa)],
        ["Average CGPA", str(ov.average_cgpa)],
        ["Highest SGPA", f"{ov.highest_sgpa} ({ov.topper_name})"],
        ["Lowest SGPA", str(ov.lowest_sgpa)],
        ["Departments Analyzed", str(len(analytics.branch_stats))],
        ["Subjects Analyzed", str(len(analytics.subject_stats))],
    ]
    pdf.add_data_table(headers, rows, col_widths=[250, 245])

    pdf.add_page_break()
