"""
scraper.py
----------
Browser automation for the RGPV result portal using Playwright.

CAPTCHA handling strategy (deliberately manual, not OCR/auto-solve):
    RGPV issues a fresh image captcha per request. Rather than trying to
    auto-solve it (unreliable, and edges into bypassing a site's abuse
    protection), this script opens a *visible* (non-headless) browser
    window and pauses for a human to type the captcha into the page
    itself, then continues once you press Enter in the terminal. This
    keeps the automation within "a human is operating the browser,
    Python just fills the repetitive fields" territory.

You MUST inspect the live RGPV result page's HTML (view-source / devtools)
and update the SELECTORS below to match. RGPV's markup / URL has changed
across the years, so a hardcoded selector set copied from an old thread
will not reliably work.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# CONFIG - update these after inspecting the live page
# ---------------------------------------------------------------------------

RESULT_PAGE_URL = "https://result.rgpv.ac.in/Result/BErslt.aspx"  # VERIFY current URL first
PROGRAM_SELECT_URL = "https://result.rgpv.ac.in/Result/ProgramSelect.aspx"

# CSS selectors on the RGPV form - PLACEHOLDERS, verify against live DOM
SELECTOR_ENROLLMENT_INPUT = "#ctl00_ContentPlaceHolder1_txtrollno"
SELECTOR_CAPTCHA_INPUT = "#ctl00_ContentPlaceHolder1_TextBox1"
SELECTOR_SUBMIT_BUTTON = "#ctl00_ContentPlaceHolder1_btnviewresult"
SELECTOR_RESULT_CONTAINER = ".gridtable, table"
SELECTOR_SEMESTER_SELECT = "#ctl00_ContentPlaceHolder1_drpSemester"



@dataclass
class FetchResult:
    enrollment: str
    html: Optional[str]
    error: Optional[str] = None


class RGPVScraper:
    def __init__(self, headless: bool = False, min_delay: float = 3.0, max_delay: float = 6.0):
        # headless=False on purpose: a human needs to see + solve the captcha.
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._pw = None
        self._browser = None
        self._page: Optional[Page] = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _polite_delay(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def fetch_result_html(self, enrollment: str, sem: Optional[str] = None, program: str = "B.Tech.", max_retries: int = 3) -> FetchResult:
        """
        Navigate to the result page, fill in the enrollment number, pause
        for the human to solve the captcha, submit, and return the
        rendered result HTML.
        """
        page = self._page
        assert page is not None, "Use RGPVScraper as a context manager"

        # Handle dialogs (alerts) automatically
        dialog_message = [None]
        def handle_dialog(dialog):
            dialog_message[0] = dialog.message
            print(f"\n[Browser Alert] {dialog.message}")
            try:
                dialog.dismiss()
            except Exception:
                pass

        page.on("dialog", handle_dialog)

        for attempt in range(1, max_retries + 1):
            try:
                # 1. Navigate to Program Selection Page first to establish correct session state
                page.goto(PROGRAM_SELECT_URL, timeout=30000)
                page.wait_for_selector("input[name='radlstProgram']", timeout=15000)
                
                # 2. Find and select the specified program radio button
                radios = page.query_selector_all("input[name='radlstProgram']")
                target_radio_id = None
                for r in radios:
                    r_id = r.get_attribute("id")
                    label = page.query_selector(f"label[for='{r_id}']")
                    if label and label.inner_text().strip().lower() == program.strip().lower():
                        target_radio_id = r_id
                        break
                
                if target_radio_id:
                    page.click(f"#{target_radio_id}")
                    # Wait for navigation/redirection to load the query form
                    page.wait_for_selector(SELECTOR_ENROLLMENT_INPUT, timeout=20000)
                else:
                    # Fallback to direct navigation if program isn't found
                    print(f"[{enrollment}] Warning: Program '{program}' not found on list. Navigating directly.")
                    page.goto(RESULT_PAGE_URL, timeout=30000)
                    page.wait_for_selector(SELECTOR_ENROLLMENT_INPUT, timeout=15000)

                # 3. Select the semester if provided
                if sem:
                    try:
                        page.select_option(SELECTOR_SEMESTER_SELECT, value=str(sem))
                    except Exception as e:
                        print(f"[{enrollment}] Warning: Could not select semester '{sem}': {e}")
                        
                page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)

                print(f"\n[{enrollment}] Please solve the CAPTCHA in the browser window.")
                print("Options:")
                print("  -> Option A: Type CAPTCHA in the browser and click 'View Result' or press Enter in the browser.")
                print("  -> Option B: Type CAPTCHA in the browser, select the terminal window, and press the ENTER key.")

                # Clear keypress buffer (Windows only)
                import msvcrt
                while msvcrt.kbhit():
                    msvcrt.getch()

                result_html = None
                while True:
                    try:
                        content = page.content()
                    except Exception:
                        # Page is still navigating — skip this tick
                        page.wait_for_timeout(500)
                        continue
                    from automation.parser import is_not_found
                    
                    # Verify that result page is loaded with actual student results or not-found message
                    if "SGPA" in content or "CGPA" in content or is_not_found(content):
                        result_html = content
                        break

                    # Check if an alert was triggered
                    if dialog_message[0] is not None:
                        msg = dialog_message[0]
                        dialog_message[0] = None
                        
                        m = msg.lower()
                        # If the alert indicates the record wasn't found
                        if "not found" in m or "invalid" in m or "no record" in m or "does not exist" in m:
                            print(f"[{enrollment}] Alert indicates record not found: {msg}")
                            result_html = f"<html><body>Result not found: {msg}</body></html>"
                            break
                        else:
                            # CAPTCHA failure
                            print(f"[{enrollment}] Submit failed: {msg}. Please re-enter the CAPTCHA in the browser.")
                            # Refill enrollment in case it was cleared
                            try:
                                page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)
                            except Exception:
                                pass

                    # Check for terminal keypress (Option B)
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        # If enter key (carriage return \r or newline \n)
                        if key in (b'\r', b'\n'):
                            print("Submit triggered from terminal...")
                            try:
                                page.click(SELECTOR_SUBMIT_BUTTON)
                            except Exception as e:
                                print(f"Error clicking submit button: {e}")

                    page.wait_for_timeout(500)  # Wait 500ms before next check

                page.remove_listener("dialog", handle_dialog)
                self._polite_delay()
                return FetchResult(enrollment=enrollment, html=result_html)

            except PWTimeout:
                print(f"[{enrollment}] Timed out on attempt {attempt}/{max_retries}.")
                if attempt == max_retries:
                    page.remove_listener("dialog", handle_dialog)
                    return FetchResult(enrollment=enrollment, html=None, error="timeout")
                self._polite_delay()
            except Exception as exc:  # noqa: BLE001
                print(f"[{enrollment}] Error on attempt {attempt}/{max_retries}: {exc}")
                exc_str = str(exc).lower()
                # Playwright's exact wording: "Target page, context or browser has been closed"
                _closed_signals = ("target closed", "browser closed", "context closed",
                                   "has been closed", "target page", "browser has been")
                if any(sig in exc_str for sig in _closed_signals):
                    page.remove_listener("dialog", handle_dialog)
                    return FetchResult(enrollment=enrollment, html=None, error="Browser closed by user")
                if attempt == max_retries:
                    page.remove_listener("dialog", handle_dialog)
                    return FetchResult(enrollment=enrollment, html=None, error=str(exc))
                self._polite_delay()

        page.remove_listener("dialog", handle_dialog)
        return FetchResult(enrollment=enrollment, html=None, error="unknown")
