"""
scraper.py
----------
Browser automation for the RGPV result portal using Playwright.

CAPTCHA handling strategy: Auto-solve via ddddocr (OCR).
    RGPV issues a fresh image captcha per request. This script uses
    ddddocr (a pure-Python OCR library) to automatically capture the
    CAPTCHA image, recognize the text, fill it in, and submit. If OCR
    fails, it auto-retries with a fresh CAPTCHA. A manual fallback is
    still available via terminal keypress (Enter) for edge cases.

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

# CAPTCHA image selector - flexible to handle RGPV's ASP.NET naming
SELECTOR_CAPTCHA_IMAGE = "img[id$='imgCaptcha'], img[src*='CaptchaImage'], img[src*='captcha'], #ctl00_ContentPlaceHolder1_imgCaptcha"

# Max auto-solve attempts per student before falling back to manual
MAX_CAPTCHA_RETRIES = 12


# ---------------------------------------------------------------------------
# OCR Engine (lazy-loaded singleton to avoid slow import on every call)
# ---------------------------------------------------------------------------
_ocr_engine = None

def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        import ddddocr
        _ocr_engine = ddddocr.DdddOcr(show_ad=False)
        print("[OCR] ddddocr engine initialized.")
    return _ocr_engine


@dataclass
class FetchResult:
    enrollment: str
    html: Optional[str]
    error: Optional[str] = None


class RGPVScraper:
    def __init__(self, headless: bool = False, min_delay: float = 1.0, max_delay: float = 2.0):
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

    def _solve_captcha_ocr(self, page: Page, prev_src: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
        """
        Locate the CAPTCHA image on the page, wait for it to reload if prev_src is provided,
        screenshot it, and use ddddocr to recognize the text.
        Returns (cleaned_text, current_src) or (None, None).
        """
        try:
            from PIL import Image
            import io
            
            # Wait for the captcha image to be present, have a new src (if prev_src is provided), and be fully loaded
            js_fn = """
                (args) => {
                    const [selector, prevSrc] = args;
                    const img = document.querySelector(selector);
                    if (!img) return false;
                    if (prevSrc && img.getAttribute('src') === prevSrc) {
                        return false;
                    }
                    return img.complete && img.naturalWidth > 0;
                }
            """
            try:
                page.wait_for_function(js_fn, arg=[SELECTOR_CAPTCHA_IMAGE, prev_src], timeout=12000)
            except Exception as e:
                print(f"[OCR] Timeout/error waiting for new CAPTCHA image: {e}")
                # Fallback to query selector if wait_for_function fails/times out
            
            # Fetch captcha image element, retrying in case of stale DOM during page reloads
            captcha_img = None
            for _ in range(5):
                try:
                    captcha_img = page.query_selector(SELECTOR_CAPTCHA_IMAGE)
                    if captcha_img:
                        captcha_img.get_attribute("src")
                        break
                except Exception:
                    page.wait_for_timeout(200)
            
            if not captcha_img:
                print("[OCR] CAPTCHA image element not found on page.")
                return None, None
            
            current_src = captcha_img.get_attribute("src")
            page.wait_for_timeout(300) # Give it a tiny extra moment to fully load/render image pixels

            # Take a screenshot of the CAPTCHA image element
            img_bytes = captcha_img.screenshot()
            
            # Load and preprocess with Pillow
            img = Image.open(io.BytesIO(img_bytes))
            
            # Paste transparent PNGs on solid white backgrounds
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1])
                img = background
            else:
                img = img.convert("RGB")
                
            # Resize (scale up 1.5x) to sharpen strokes
            img = img.resize((int(img.width * 1.5), int(img.height * 1.5)), Image.Resampling.LANCZOS)
            
            # Grayscale
            img = img.convert("L")
            
            out_bytes = io.BytesIO()
            img.save(out_bytes, format="PNG")
            
            # Run OCR
            ocr = _get_ocr()
            result = ocr.classification(out_bytes.getvalue())
            
            # Clean and return (convert to uppercase as RGPV CAPTCHA is uppercase alphanumeric)
            cleaned = result.strip().replace(" ", "").upper()
            
            # Verify if it contains only alphanumeric characters and is of correct length
            import string
            allowed_chars = set(string.ascii_letters + string.digits)
            is_valid = all(c in allowed_chars for c in cleaned) and len(cleaned) >= 4
            
            if not is_valid:
                print(f"[OCR] Warning: OCR output '{cleaned}' contains invalid characters or is too short. Refreshing CAPTCHA...")
                return None, current_src
                
            return cleaned, current_src
        except Exception as e:
            print(f"[OCR] Error during CAPTCHA recognition: {e}")
            return None, None

    def fetch_result_html(self, enrollment: str, sem: Optional[str] = None, program: str = "B.Tech.", max_retries: int = 3) -> FetchResult:
        """
        Navigate to the result page, fill in the enrollment number,
        auto-solve the CAPTCHA via OCR, submit, and return the
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

        # Clear any existing dialog listeners to avoid duplicates
        try:
            page.remove_all_listeners("dialog")
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
                    if label:
                        lbl_norm = label.inner_text().replace(".", "").replace(" ", "").replace("-", "").lower().strip()
                        prog_norm = program.replace(".", "").replace(" ", "").replace("-", "").lower().strip()
                        if lbl_norm == prog_norm:
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
                        current_sem = page.eval_on_selector(SELECTOR_SEMESTER_SELECT, "el => el.value")
                        if current_sem != str(sem):
                            print(f"[{enrollment}] Selecting semester '{sem}' (was '{current_sem}')...")
                            base_img = page.query_selector(SELECTOR_CAPTCHA_IMAGE)
                            base_src = base_img.get_attribute("src") if base_img else None
                            
                            page.select_option(SELECTOR_SEMESTER_SELECT, value=str(sem))
                            
                            if base_src:
                                js_fn = """
                                    (args) => {
                                        const [selector, prevSrc] = args;
                                        const img = document.querySelector(selector);
                                        if (!img) return false;
                                        if (img.getAttribute('src') === prevSrc) {
                                            return false;
                                        }
                                        return img.complete && img.naturalWidth > 0;
                                    }
                                """
                                try:
                                    page.wait_for_function(js_fn, arg=[SELECTOR_CAPTCHA_IMAGE, base_src], timeout=8000)
                                except Exception:
                                    page.wait_for_timeout(1000)
                            else:
                                page.wait_for_timeout(1500)
                    except Exception as e:
                        print(f"[{enrollment}] Warning: Could not select semester '{sem}': {e}")
                        
                page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)

                # 4. Auto CAPTCHA solving loop
                captcha_solved = False
                prev_captcha_src = None
                for captcha_attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
                    # Clear any previous dialog
                    dialog_message[0] = None

                    # If semester is reset to default (due to wrong CAPTCHA page reload), re-select it
                    if sem:
                        try:
                            current_sem = page.eval_on_selector(SELECTOR_SEMESTER_SELECT, "el => el.value")
                            if current_sem != str(sem):
                                print(f"[{enrollment}] Re-selecting semester '{sem}' (was '{current_sem}')...")
                                base_img = page.query_selector(SELECTOR_CAPTCHA_IMAGE)
                                base_src = base_img.get_attribute("src") if base_img else None
                                
                                page.select_option(SELECTOR_SEMESTER_SELECT, value=str(sem))
                                
                                # Wait for the semester postback to refresh the CAPTCHA src
                                if base_src:
                                    js_fn = """
                                        (args) => {
                                            const [selector, prevSrc] = args;
                                            const img = document.querySelector(selector);
                                            if (!img) return false;
                                            if (img.getAttribute('src') === prevSrc) {
                                                return false;
                                            }
                                            return img.complete && img.naturalWidth > 0;
                                        }
                                    """
                                    try:
                                        page.wait_for_function(js_fn, arg=[SELECTOR_CAPTCHA_IMAGE, base_src], timeout=8000)
                                    except Exception:
                                        page.wait_for_timeout(1000)
                                else:
                                    page.wait_for_timeout(1500)
                        except Exception as e:
                            print(f"[{enrollment}] Warning: Could not select semester: {e}")

                    # Screenshot and OCR the CAPTCHA, waiting for a new image to load
                    captcha_text, prev_captcha_src = self._solve_captcha_ocr(page, prev_captcha_src)
                    
                    if not captcha_text:
                        print(f"[{enrollment}] CAPTCHA OCR returned empty. Retrying...")
                        # Reload the page to get a fresh CAPTCHA
                        page.goto(RESULT_PAGE_URL, timeout=30000)
                        page.wait_for_selector(SELECTOR_ENROLLMENT_INPUT, timeout=15000)
                        if sem:
                            try:
                                page.select_option(SELECTOR_SEMESTER_SELECT, value=str(sem))
                            except Exception:
                                pass
                        page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)
                        continue

                    print(f"[{enrollment}] CAPTCHA OCR attempt {captcha_attempt}/{MAX_CAPTCHA_RETRIES}: \"{captcha_text}\"")

                    # Fill the enrollment and CAPTCHA input and submit
                    try:
                        page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)
                        page.fill(SELECTOR_CAPTCHA_INPUT, captcha_text)
                    except Exception as e:
                        print(f"[{enrollment}] Could not fill CAPTCHA input: {e}")
                        continue

                    try:
                        page.click(SELECTOR_SUBMIT_BUTTON)
                    except Exception as e:
                        print(f"[{enrollment}] Could not click submit: {e}")
                        continue

                    # Wait for result page or alert dialog
                    page.wait_for_timeout(1500)

                    # Check if result page loaded
                    try:
                        content = page.content()
                    except Exception:
                        page.wait_for_timeout(500)
                        try:
                            content = page.content()
                        except Exception:
                            continue

                    from automation.parser import is_not_found

                    if "SGPA" in content or "CGPA" in content or is_not_found(content):
                        captcha_solved = True
                        page.remove_listener("dialog", handle_dialog)
                        self._polite_delay()
                        return FetchResult(enrollment=enrollment, html=content)

                    # Check if an alert was triggered
                    if dialog_message[0] is not None:
                        msg = dialog_message[0]
                        dialog_message[0] = None
                        
                        m = msg.lower()
                        # If the alert indicates the record wasn't found
                        if "not found" in m or "invalid" in m or "no record" in m or "does not exist" in m:
                            print(f"[{enrollment}] Alert indicates record not found: {msg}")
                            result_html = f"<html><body>Result not found: {msg}</body></html>"
                            page.remove_listener("dialog", handle_dialog)
                            self._polite_delay()
                            return FetchResult(enrollment=enrollment, html=result_html)
                        else:
                            # CAPTCHA failure - will retry automatically
                            print(f"[{enrollment}] Wrong CAPTCHA (\"{captcha_text}\"). Auto-retrying...")
                            # Refill enrollment in case it was cleared
                            try:
                                page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)
                            except Exception:
                                pass
                            continue

                # If all CAPTCHA attempts failed, fall back to manual mode
                if not captcha_solved:
                    print(f"\n[{enrollment}] Auto-solve exhausted ({MAX_CAPTCHA_RETRIES} attempts). Falling back to MANUAL mode.")
                    print(f"[{enrollment}] Please solve the CAPTCHA in the browser window and press Enter.")
                    
                    # Clear keypress buffer (Windows only)
                    import msvcrt
                    while msvcrt.kbhit():
                        msvcrt.getch()

                    result_html = None
                    while True:
                        try:
                            content = page.content()
                        except Exception:
                            page.wait_for_timeout(500)
                            continue
                        from automation.parser import is_not_found
                        
                        if "SGPA" in content or "CGPA" in content or is_not_found(content):
                            result_html = content
                            break

                        if dialog_message[0] is not None:
                            msg = dialog_message[0]
                            dialog_message[0] = None
                            
                            m = msg.lower()
                            if "not found" in m or "invalid" in m or "no record" in m or "does not exist" in m:
                                print(f"[{enrollment}] Alert indicates record not found: {msg}")
                                result_html = f"<html><body>Result not found: {msg}</body></html>"
                                break
                            else:
                                print(f"[{enrollment}] Submit failed: {msg}. Please re-enter the CAPTCHA.")
                                try:
                                    page.fill(SELECTOR_ENROLLMENT_INPUT, enrollment)
                                except Exception:
                                    pass

                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key in (b'\r', b'\n'):
                                print("Submit triggered from terminal...")
                                try:
                                    page.click(SELECTOR_SUBMIT_BUTTON)
                                except Exception as e:
                                    print(f"Error clicking submit button: {e}")

                        page.wait_for_timeout(500)

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
