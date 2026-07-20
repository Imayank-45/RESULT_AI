"""
generate_report.py
------------------
Main orchestrator and CLI entry point for the AI Report Generator.

Usage:
    python -m report_generator.generate_report --input data/results.xlsx
    python -m report_generator.generate_report --input data/current.xlsx --compare data/previous.xlsx
    python -m report_generator.generate_report --input data/results.xlsx --college "RGPV" --department "IT" --semester 3
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from report_generator.config import ReportConfig
from report_generator.data_loader import load_from_excel, load_from_records, ReportDataset
from report_generator.analytics_engine import compute_analytics
from report_generator.pdf_builder import PDFReport
from report_generator.chart_renderer import cleanup_temp_charts


# ═══════════════════════════════════════════════════════════════════════
#  SECTION IMPORTS
# ═══════════════════════════════════════════════════════════════════════

from report_generator.report_sections import (
    cover_page,
    table_of_contents,
    executive_summary,
    overall_statistics,
    branch_analysis,
    semester_analysis,
    subject_analysis,
    topper_analysis,
    student_pages,
    grade_distribution,
    pass_percentage,
    backlog_analysis,
    heatmaps,
    risk_analysis,
    improvement_analysis,
    comparison_analysis,
    ai_insights_section,
    ai_recommendations,
)


# ═══════════════════════════════════════════════════════════════════════
#  REPORT GENERATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def generate_report(
    input_path: Optional[str] = None,
    compare_path: Optional[str] = None,
    records: Optional[List[Dict[str, Any]]] = None,
    college_name: str = "Rajiv Gandhi Proudyogiki Vishwavidyalaya",
    department: str = "Department of Information Technology",
    semester: str = "",
    program: str = "B.Tech.",
    output_dir: str = "data/reports",
    job_id: str = "",
    logo_path: Optional[str] = None,
    max_student_pages: Optional[int] = 100,
) -> str:
    """
    Generate a professional PDF report.

    Args:
        input_path: Path to Excel file with result data.
        compare_path: Optional path to previous result Excel for comparison.
        records: Optional in-memory records list (alternative to Excel).
        college_name: College name for cover page.
        department: Department name.
        semester: Semester number.
        program: Program name (e.g. B.Tech.).
        output_dir: Directory to save the PDF.
        job_id: Job identifier.
        logo_path: Optional logo image path.
        max_student_pages: Optional maximum student detail pages limit.

    Returns:
        Path to the generated PDF file.
    """
    start_time = time.time()
    print("\n" + "=" * 65)
    print("  ResultAI - Automatic AI Report Generator v1.0")
    print("=" * 65)

    # -- Configuration --
    config = ReportConfig(
        college_name=college_name,
        department=department,
        semester=semester,
        program=program,
        output_dir=output_dir,
        job_id=job_id,
        logo_path=logo_path,
        max_student_pages=max_student_pages or 100,
    )

    # -- Step 1: Load Data --
    print("\n[1/6] Loading data...")
    if input_path:
        dataset = load_from_excel(input_path, config)
        print(f"  [OK] Loaded {len(dataset.records)} records from {input_path}")
    elif records:
        dataset = load_from_records(records, config)
        print(f"  [OK] Loaded {len(dataset.records)} records from memory")
    else:
        raise ValueError("Either input_path or records must be provided.")

    # Load comparison data if available
    if compare_path and os.path.exists(compare_path):
        comp_dataset = load_from_excel(compare_path, config)
        dataset.comparison_records = comp_dataset.records
        print(f"  [OK] Loaded {len(comp_dataset.records)} comparison records from {compare_path}")

    # Override job_id if provided
    if job_id:
        dataset.job_id = job_id

    # -- Step 2: Compute Analytics --
    print("\n[2/6] Computing analytics...")
    analytics = compute_analytics(dataset)
    print(f"  [OK] Overall: {analytics.overall.total_students} students, "
          f"{analytics.overall.pass_percentage}% pass rate, "
          f"avg SGPA {analytics.overall.average_sgpa}")
    print(f"  [OK] Branches: {len(analytics.branch_stats)}")
    print(f"  [OK] Subjects: {len(analytics.subject_stats)}")
    print(f"  [OK] At-risk students: {len(analytics.students_at_risk)}")

    # -- Step 3: Setup PDF --
    print("\n[3/6] Initializing PDF builder...")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = dataset.prefix or "report"
    output_path = os.path.join(output_dir, f"ResultAI_Report_{prefix}_{timestamp}.pdf")
    config.job_id = dataset.job_id

    pdf = PDFReport(config, output_path)
    print(f"  [OK] Output: {output_path}")

    # ── Step 4: Render Sections ──
    print("\n[4/6] Rendering report sections...")

    sections = [
        ("Cover Page", cover_page),
        ("Table of Contents", table_of_contents),
        ("Executive Summary", executive_summary),
        ("Overall Statistics", overall_statistics),
        ("Branch Analysis", branch_analysis),
        ("Semester Analysis", semester_analysis),
        ("Subject Analysis", subject_analysis),
        ("Topper Analysis", topper_analysis),
        ("Student Details", student_pages),
        ("Grade Distribution", grade_distribution),
        ("Pass Percentage", pass_percentage),
        ("Backlog Analysis", backlog_analysis),
        ("Heatmaps", heatmaps),
        ("Risk Analysis", risk_analysis),
        ("Improvement Analysis", improvement_analysis),
        ("Comparison Analysis", comparison_analysis),
        ("AI Insights", ai_insights_section),
        ("AI Recommendations", ai_recommendations),
    ]

    for i, (name, module) in enumerate(sections, 1):
        try:
            print(f"  [{i}/{len(sections)}] Rendering {name}...")
            module.render(pdf, dataset, analytics)
        except Exception as e:
            print(f"  [WARN] Error rendering {name}: {e}")

    # -- Step 5: Build PDF --
    print("\n[5/6] Building PDF document...")
    try:
        output = pdf.build()
        print(f"  [OK] PDF generated successfully!")
    except Exception as e:
        print(f"  [ERR] Error building PDF: {e}")
        raise

    # -- Step 6: Cleanup --
    print("\n[6/6] Cleaning up temporary files...")
    cleanup_temp_charts()
    print(f"  [OK] Temp files cleaned")

    elapsed = round(time.time() - start_time, 2)
    file_size = os.path.getsize(output) if os.path.exists(output) else 0
    size_mb = round(file_size / (1024 * 1024), 2)

    print("\n" + "=" * 65)
    print(f"  [SUCCESS] REPORT GENERATED SUCCESSFULLY")
    print(f"  File: {output}")
    print(f"  Size: {size_mb} MB")
    print(f"  Time: {elapsed}s")
    print(f"  Students: {analytics.overall.total_students}")
    print(f"  Sections: {len(sections)}")
    print("=" * 65 + "\n")

    return output


# ═══════════════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ResultAI — Automatic AI Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m report_generator.generate_report --input data/results.xlsx
  python -m report_generator.generate_report --input data/current.xlsx --compare data/previous.xlsx
  python -m report_generator.generate_report --input data/results.xlsx --college "RGPV" --semester 3
        """
    )

    parser.add_argument("--input", required=True, help="Path to Excel file with result data")
    parser.add_argument("--compare", default=None, help="Path to previous result Excel for comparison")
    parser.add_argument("--college", default="Rajiv Gandhi Proudyogiki Vishwavidyalaya",
                        help="College name for cover page")
    parser.add_argument("--department", default="Department of Information Technology",
                        help="Department name")
    parser.add_argument("--semester", default="", help="Semester number")
    parser.add_argument("--program", default="B.Tech.", help="Program name")
    parser.add_argument("--output-dir", default="data/reports", help="Output directory for PDF")
    parser.add_argument("--job-id", default="", help="Job ID for the report")

    args = parser.parse_args()

    try:
        output = generate_report(
            input_path=args.input,
            compare_path=args.compare,
            college_name=args.college,
            department=args.department,
            semester=args.semester,
            program=args.program,
            output_dir=args.output_dir,
            job_id=args.job_id,
        )
    except FileNotFoundError as e:
        print(f"\n[ERR] Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
