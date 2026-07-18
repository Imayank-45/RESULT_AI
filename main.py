"""
main.py
-------
CLI entry point for RGPV Result Fetcher.

Usage:
    python main.py --prefix 0105IT2410 --start 1 --end 20 [--pad 2]

This will, for each roll number in [start, end]:
    1. Build enrollment = prefix + str(roll).zfill(pad)
    2. Open a browser window and let you solve the captcha for that enrollment
    3. Parse the returned result page
    4. Append it to the running list

...then write everything to an Excel file named
    RGPV_Result_<prefix>_<start>-<end>.xlsx

IMPORTANT: this only works against a *currently correct* RESULT_PAGE_URL and
selector set in scraper.py. RGPV's site markup has changed multiple times;
open the live page in your browser, inspect the form fields, and update
scraper.py's SELECTOR_* constants before running this for real.
"""

from __future__ import annotations

import argparse
import sys

from automation.scraper import RGPVScraper
from automation.parser import parse_result_html, ResultNotFound
from automation.excel_writer import write_excel


def build_enrollment(prefix: str, roll: int, pad: int) -> str:
    return f"{prefix}{str(roll).zfill(pad)}"


def main():
    ap = argparse.ArgumentParser(description="RGPV bulk result fetcher")
    ap.add_argument("--prefix", required=True, help="Enrollment prefix, e.g. 0105IT2410")
    ap.add_argument("--start", type=int, required=True, help="Start roll number")
    ap.add_argument("--end", type=int, required=True, help="End roll number (inclusive)")
    ap.add_argument("--pad", type=int, default=2, help="Zero-padding width for roll number (default: 2)")
    ap.add_argument("--sem", type=str, help="Semester to select, e.g. 1, 2, 3... (optional)")
    ap.add_argument("--program", default="B.Tech.", help="Program name, e.g. B.Tech., B.E., B.Pharmacy, etc. (default: B.Tech.)")
    ap.add_argument("--headless", action="store_true",
                     help="Run headless (NOTE: you won't be able to solve captchas this way; "
                          "only use if you've wired up an alternate captcha solution)")
    args = ap.parse_args()

    if args.start > args.end:
        print("start must be <= end", file=sys.stderr)
        sys.exit(1)

    records = []
    total = args.end - args.start + 1
    pass_count = fail_count = not_found_count = error_count = 0

    with RGPVScraper(headless=args.headless) as scraper:
        for roll in range(args.start, args.end + 1):
            enrollment = build_enrollment(args.prefix, roll, args.pad)
            print(f"\n=== Processing {enrollment} ({roll - args.start + 1}/{total}) ===")

            fetch_result = scraper.fetch_result_html(enrollment, sem=args.sem, program=args.program)

            if fetch_result.error:
                print(f"[{enrollment}] Failed: {fetch_result.error}")
                records.append({"enrollment": enrollment, "not_found": True})
                error_count += 1
                # If the browser was closed, stop the whole run — no point continuing
                if "browser closed" in fetch_result.error.lower() or "closed by user" in fetch_result.error.lower():
                    print("\n[System] Browser window was closed. Stopping scraper.")
                    break
                continue

            try:
                record = parse_result_html(fetch_result.html, enrollment)
                records.append(record)
                if record["result"] == "PASS":
                    pass_count += 1
                elif record["result"] == "FAIL":
                    fail_count += 1
                print(f"[{enrollment}] {record['result']} | SGPA={record['sgpa']} CGPA={record['cgpa']}")
            except ResultNotFound:
                print(f"[{enrollment}] No record found.")
                records.append({"enrollment": enrollment, "not_found": True})
                not_found_count += 1

    import os
    os.makedirs("data", exist_ok=True)
    out_path = f"data/RGPV_Result_{args.prefix}_{args.start}-{args.end}.xlsx"
    write_excel(records, out_path)

    print("\n--- Summary ---")
    print(f"Total processed: {total}")
    print(f"Pass: {pass_count}")
    print(f"Fail: {fail_count}")
    print(f"Not found: {not_found_count}")
    print(f"Errors: {error_count}")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
