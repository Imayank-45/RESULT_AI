"""
report_generator
================
Automatic AI Report Generator for ResultAI.

Generates professional 40–50 page PDF reports from scraped RGPV result data.

Usage:
    from report_generator import generate_report

    generate_report(
        input_path="data/RGPV_Result_0105IT2410_1-20.xlsx",
        college_name="RGPV Bhopal",
        department="Information Technology",
        semester="3",
        program="B.Tech."
    )
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "ResultAI"

from report_generator.generate_report import generate_report

__all__ = ["generate_report"]
