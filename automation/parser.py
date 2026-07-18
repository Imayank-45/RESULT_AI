"""
parser.py
---------
Parses a single RGPV result page's HTML into a structured dict.

The RGPV result table layout has shifted across semesters/years, so this
parser does NOT hardcode subject codes. Instead it:
  1. Finds the results table on the page.
  2. Reads the header row to discover subject columns dynamically.
  3. Reads the body rows to build a {subject_code: grade} map.
  4. Separately extracts SGPA / CGPA / Result status, which usually live
     in labeled cells or a summary block rather than the main grid.

NOTE: Because the live markup can change, `find_result_table` and the two
regexes below are the most likely things you'll need to tweak after you
inspect the actual page HTML (e.g. via browser devtools) for the current
semester's result. Everything else in this file should keep working as-is.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

NOT_FOUND_PATTERNS = [
    r"no\s*record\s*found",
    r"invalid\s*enrollment",
    r"result\s*not\s*found",
    r"data\s*not\s*available",
]

SGPA_RE = re.compile(r"SGPA[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
CGPA_RE = re.compile(r"CGPA[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


class ResultNotFound(Exception):
    """Raised when the page indicates no record exists for the enrollment number."""


def is_not_found(page_text: str) -> bool:
    text = page_text.lower()
    return any(re.search(pat, text) for pat in NOT_FOUND_PATTERNS)


def find_result_table(soup: BeautifulSoup):
    """
    Try a few heuristics to find the actual grades table, since RGPV's
    ASP.NET output wraps content in many nested layout tables.

    Heuristic: the correct table is the one whose header row contains
    something that looks like a subject-code pattern (letters+digits,
    e.g. IT301, ES301, BT107) in multiple cells.
    """
    subject_code_re = re.compile(r"^[A-Z]{2,4}\-?\d{3,4}[\-A-Z0-9]*$")
    candidate_tables = soup.find_all("table")

    best_table = None
    best_score = 0
    for table in candidate_tables:
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        score = sum(
            1 for c in header_cells if subject_code_re.match(c.get_text(strip=True))
        )
        if score > best_score:
            best_score = score
            best_table = table

    return best_table if best_score >= 2 else None


def parse_result_html(html: str, enrollment: str) -> dict:
    """
    Parse a single result page's HTML.

    Returns a dict:
        {
            "enrollment": str,
            "name": str,
            "subjects": {subject_code: grade, ...},   # in table order
            "sgpa": str | None,
            "cgpa": str | None,
            "result": "PASS" | "FAIL" | "UNKNOWN",
            "fail_subjects": [subject_code, ...],
        }

    Raises ResultNotFound if the page indicates no record exists.
    """
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text(" ", strip=True)

    if is_not_found(page_text):
        raise ResultNotFound(f"No record found for {enrollment}")

    record = {
        "enrollment": enrollment,
        "name": "",
        "subjects": {},
        "sgpa": None,
        "cgpa": None,
        "result": "UNKNOWN",
        "fail_subjects": [],
    }

    # 1. Extract student name
    name_el = soup.find(id=re.compile(r"lblName", re.IGNORECASE))
    if name_el:
        record["name"] = name_el.get_text(strip=True)

    # 2. Extract SGPA, CGPA, and Result Status using specific ASP.NET control IDs
    sgpa_el = soup.find(id=re.compile(r"lblSGPA", re.IGNORECASE))
    if sgpa_el:
        record["sgpa"] = sgpa_el.get_text(strip=True)
        
    cgpa_el = soup.find(id=re.compile(r"lblcgpa", re.IGNORECASE))
    if cgpa_el:
        record["cgpa"] = cgpa_el.get_text(strip=True)
        
    result_el = soup.find(id=re.compile(r"lblResult", re.IGNORECASE))
    result_status = result_el.get_text(strip=True).upper() if result_el else ""

    # Fallback to regex if specific elements are missing
    if not record["sgpa"]:
        sgpa_match = SGPA_RE.search(page_text)
        if sgpa_match:
            record["sgpa"] = sgpa_match.group(1)
            
    if not record["cgpa"]:
        cgpa_match = CGPA_RE.search(page_text)
        if cgpa_match:
            record["cgpa"] = cgpa_match.group(1)

    # 3. Extract subjects and grades (supports both unified and separate/nested tables)
    subject_code_re = re.compile(r"^[A-Z]{2,4}\-?\d{3,4}[\-A-Z0-9\s\[\]\(\)]*$", re.IGNORECASE)
    
    # Iterate through all rows in all tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) == 4:
                subj_code = cells[0]
                grade = cells[3]
                # Avoid matching column headers (like "Subject", "Total Credit", etc.)
                if subj_code and grade and subject_code_re.match(subj_code) and "subject" not in subj_code.lower():
                    record["subjects"][subj_code] = grade

    # If no subjects found via simple row matching, fall back to the original layout table parser
    if not record["subjects"]:
        table = find_result_table(soup)
        if table is not None:
            rows = table.find_all("tr")
            headers = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                if len(cells) != len(headers):
                    continue
                for header, value in zip(headers, cells):
                    if not header or not value:
                        continue
                    if re.match(r"^[A-Z]{2,4}\-?\d{3,4}[\-A-Z0-9\s\[\]\(\)]*$", header, re.IGNORECASE):
                        record["subjects"][header] = value

    fail_subjects = [
        code
        for code, grade in record["subjects"].items()
        if grade.strip().upper() in {"F", "FAIL", "AB", "ABSENT", "RL"}
    ]
    record["fail_subjects"] = fail_subjects

    # Determine PASS/FAIL status
    if "PASS" in result_status or ("PASS" in page_text.upper() and not fail_subjects):
        record["result"] = "PASS"
    elif "FAIL" in result_status or fail_subjects or "FAIL" in page_text.upper():
        record["result"] = "FAIL"
    else:
        record["result"] = "UNKNOWN"

    return record
