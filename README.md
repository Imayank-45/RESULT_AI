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
*   `automation/scraper.py` - Playwright automation, browser session management, and CAPTCHA polling logic.
*   `automation/parser.py` - BeautifulSoup logic for parsing result sheets, grades, names, and CGPA/SGPA values.
*   `automation/excel_writer.py` - Excel format generator using `openpyxl` to build output spreadsheets.
*   `backend/server.py` - FastAPI server with REST API and WebSocket support.
*   `frontend/` - Vite/React frontend application.
*   `requirements.txt` - Dependency versions mapping.

---

## 📊 AI Report Generator

A standalone module that automatically generates **professional 40–50 page PDF reports** from scraped result data — rivaling Power BI, McKinsey, and Deloitte analytics reports in visual quality.

### Features
- **18 report sections**: Cover page, clickable TOC, Executive Summary, Branch Analysis, Subject Analysis, Toppers, Student Details, Grade Distribution, Pass Percentage Gauge, Backlog Analysis, Heatmaps, Risk Analysis, Improvement Analysis, Comparison Analysis, AI Insights (30–50), and AI Recommendations (20+).
- **Premium charts** (bar, pie, donut, radar, heatmap, gauge, histogram, scatter, line/area) rendered via Matplotlib at 200 DPI
- **Clickable Table of Contents** with dot leaders — each entry navigates to its section bookmark
- **PDF outline bookmarks** (visible in Acrobat/Evince sidebar)
- **Rule-based AI engine** — generates natural-language observations and prioritized recommendations without any external API calls
- **Comparison mode** — supply a previous Excel file to get semester-over-semester delta charts

### Extra Dependencies (one-time install)
```powershell
venv\Scripts\python.exe -m pip install reportlab matplotlib
```

### CLI Usage

```powershell
# Basic report from Excel file
venv\Scripts\python.exe -m report_generator.generate_report --input data/RGPV_Result_0105IT2410_1-20.xlsx

# With RGPV branding + semester
venv\Scripts\python.exe -m report_generator.generate_report `
  --input data/RGPV_Result_0105IT2410_1-20.xlsx `
  --college "RGPV Bhopal" `
  --department "Information Technology" `
  --semester 3

# With comparison (semester-over-semester)
venv\Scripts\python.exe -m report_generator.generate_report `
  --input data/current.xlsx `
  --compare data/previous.xlsx `
  --college "RGPV Bhopal"
```

#### CLI Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--input` | Path to result Excel file | **Required** |
| `--compare` | Path to previous result Excel (comparison mode) | Optional |
| `--college` | College name for cover page | `Rajiv Gandhi Proudyogiki Vishwavidyalaya` |
| `--department` | Department name | `Department of Information Technology` |
| `--semester` | Semester number | *(blank)* |
| `--program` | Program name | `B.Tech.` |
| `--output-dir` | Output directory for PDF | `data/reports` |
| `--job-id` | Job identifier string | *(auto-generated)* |

### API Integration (Optional)

The report generator exposes a FastAPI router that can be mounted in `backend/server.py`:

```python
from report_generator.api import report_router
app.include_router(report_router, prefix="/api/report")
```

**Endpoints:**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/report/generate` | Generate PDF from Excel path |
| `GET` | `/api/report/download?path=…` | Download the generated PDF |
| `GET` | `/api/report/status` | Check generation status |

### Module Architecture

```
report_generator/
├── __init__.py              # Public API: from report_generator import generate_report
├── requirements.txt         # reportlab, matplotlib, numpy
├── config.py                # Colors, fonts, page dimensions, branch code mappings
├── data_loader.py           # Load from Excel / in-memory records → ReportDataset
├── analytics_engine.py      # Pure stats: SGPA, pass%, backlogs, heatmap, comparison
├── ai_insights.py           # Rule-based 30–50 insights + 20+ recommendations
├── chart_renderer.py        # Matplotlib chart factory (10 chart types, 200 DPI)
├── pdf_builder.py           # ReportLab engine: pages, header/footer, bookmarks
├── generate_report.py       # Orchestrator + CLI entry point
├── api.py                   # FastAPI router (optional mount)
└── report_sections/         # 19 modular section renderers
    ├── cover_page.py
    ├── table_of_contents.py
    ├── executive_summary.py
    ├── overall_statistics.py
    ├── branch_analysis.py
    ├── semester_analysis.py
    ├── subject_analysis.py
    ├── topper_analysis.py
    ├── student_pages.py
    ├── grade_distribution.py
    ├── pass_percentage.py
    ├── backlog_analysis.py
    ├── heatmaps.py
    ├── risk_analysis.py
    ├── improvement_analysis.py
    ├── comparison_analysis.py
    ├── ai_insights_section.py
    └── ai_recommendations.py
```

### Output

Generated PDFs are saved to `data/reports/` with the filename pattern:
```
ResultAI_Report_<prefix>_<timestamp>.pdf
```
Example: `ResultAI_Report_0105IT2410_20260719_233720.pdf`
