# RGPV Result Fetcher

Fetches semester results for a range of enrollment numbers from the RGPV result portal and exports them to a professionally formatted Excel sheet.

## Key Features & Automations
*   **Automatic Semester Selection:** Pass the `--sem` argument to select semesters 1 to 8 automatically.
*   **Automatic Program Selection:** Pass the `--program` argument (defaults to `"B.Tech."`) to select between B.Tech, B.E., B.Pharmacy, etc. and establish the correct session state automatically.
*   **Double Submission Mode:** 
    *   **In-Browser (Recommended):** Type the CAPTCHA in the browser window and press **Enter** (or click **View Result**) in the browser. The script will automatically detect the submission and proceed.
    *   **Terminal Enter:** Type the CAPTCHA in the browser, select the terminal window, and press the **ENTER** key.
*   **Dialog & Captcha Errors Handling:** Popups such as "Incorrect Captcha" are caught automatically, letting you retry. Alerts like "Result not Found" are detected as not found records and skipped immediately.
*   **Enhanced Excel Exporter:** Saves student **NAME**, **ENROLLMENT**, **RESULT STATUS**, **SGPA**, **CGPA**, and all subject-wise grades in dynamic, auto-fitted columns.
*   **Robust Subject Code Parsing:** Full support out of the box for CBCS (3-digit e.g., `BT-101`), CBGS (4-digit e.g., `CS-6001`), and hyphenated/bracketed formats (e.g. `ES301- [T]`).

---

## Setup

1. **Create the Virtual Environment:**
   ```powershell
   py -m venv venv
   ```

2. **Install Dependencies:**
   ```powershell
   venv\Scripts\pip install -r requirements.txt
   ```

3. **Install Chromium Browser for Playwright:**
   ```powershell
   venv\Scripts\playwright install chromium
   ```

---

## Running the Program

To run the program, use the following command format:

```powershell
venv\Scripts\python main.py --prefix <prefix> --start <start_roll> --end <end_roll> --pad <padding> --sem <sem> [--program <program>]
```

### Example:
To fetch results for B.Tech Semester 3 from roll number 1 to 20:
```powershell
venv\Scripts\python main.py --prefix 0105IT2410 --start 1 --end 20 --pad 2 --sem 3
```

---

## Command Line Arguments

| Argument | Description | Default / Required |
| :--- | :--- | :--- |
| `--prefix` | Enrollment number prefix, e.g. `0105IT2410` | **Required** |
| `--start` | Starting roll number (e.g. `1`) | **Required** |
| `--end` | Ending roll number (e.g. `20`) | **Required** |
| `--pad` | Zero-padding width for roll number suffix | `2` |
| `--sem` | Semester number to select, e.g. `1` to `8` | **Optional** |
| `--program` | Program to select, e.g. `B.Tech.`, `B.E.`, `B.Pharmacy` | `B.Tech.` |
| `--headless`| Runs browser in headless mode (not recommended due to CAPTCHAs) | Off |

---

## Project Structure

*   `main.py` - Command-line entry point and orchestration loop.
*   `scraper.py` - Playwright automation, browser session management, and CAPTCHA polling logic.
*   `parser.py` - BeautifulSoup logic for parsing result sheets, grades, names, and CGPA/SGPA values.
*   `excel_writer.py` - Excel format generator using `openpyxl` to build output spreadsheets.
*   `requirements.txt` - Dependency versions mapping.
