# ResultAI - RGPV Result Analytics & Dashboard Platform
## Technical Specification, Product Design & Current Implementation Status

> **Last Updated:** 2026-07-20  
> **Status:** Production Ready — Scraper Engine + AI Report Generator + Result Compare Studio Fully Integrated

---

## 🔧 TECH STACK (Current Implementation)

### Backend & Automation
| Layer | Technology | Version |
|---|---|---|
| Web Framework | **FastAPI** | ≥ 0.110.0 |
| ASGI Server | **Uvicorn** | ≥ 0.28.0 |
| Browser Automation | **Playwright (Sync API)** | ≥ 1.44.0 |
| CAPTCHA Solver | **ddddocr** | ≥ 1.6.0 |
| Image Processing | **Pillow** | ≥ 10.0.0 |
| HTML Parser | **BeautifulSoup4** | ≥ 4.12.0 |
| HTML Parser Backend | **lxml** | ≥ 5.2.0 |
| Excel Processing | **openpyxl** | ≥ 3.1.0 |
| Data Handling | **pandas** | ≥ 2.2.0 |
| Numerical Analytics | **NumPy** | ≥ 1.26.0 |
| PDF Document Engine | **ReportLab** | ≥ 4.0 |
| Data Visualization | **Matplotlib** | ≥ 3.8.0 |
| Real-time Comm | **WebSockets** | ≥ 12.0 |
| Language | **Python 3.10+** | — |

### Frontend & Analytics UI
| Layer | Technology | Version |
|---|---|---|
| UI Framework | **React** | ^19.2.7 |
| Build Tool | **Vite** | ^8.1.1 |
| Animations | **Framer Motion** | ^12.42.2 |
| Client-Side PDF Gen | **jsPDF** | ^4.2.1 |
| Client-Side Excel | **xlsx** | ^0.18.5 |
| Client PDF Parsing | **pdf.js** | CDN (v2.16.105) |
| Language | **JavaScript (JSX)** | ES Module |
| Styling | **Vanilla CSS** (Custom Design System) | — |
| Fonts | **Google Fonts** — Outfit, Inter, Fira Code | — |
| Linter | **oxlint** | ^1.71.0 |

### Runtime & DevOps
| Component | Tech |
|---|---|
| Containerization | **Docker** (Multi-stage Node 20 + Python 3.10-slim image) |
| System Libraries | `build-essential`, `libgl1`, `libglib2.0-0` (Linux OpenCV/Pillow support) |
| One-Click Launcher | **PowerShell** (`start.ps1`) |
| Data Storage | Local `.xlsx` in `/data`, PDF reports in `/data/reports`, uploads in `/data/uploads` |
| Real-time Protocol | WebSocket (`/api/ws`) + HTTP REST APIs (`/api/scrape`, `/api/report`) |

---

## 📁 CURRENT PROJECT STRUCTURE (Actual)

```
RESULT_AI/
├── main.py                    # CLI entry point for web scraper
├── requirements.txt           # Primary Python dependencies
├── README.md                  # Setup & usage guide
├── temp.md                    # Detailed Technical Specification & Architecture
├── Dockerfile                 # Multi-stage Docker deployment script
├── .dockerignore              # Docker build exclusions
├── start.ps1                  # One-click PowerShell script (builds & runs Frontend + Backend)
├── venv/                      # Python virtual environment
├── data/                      # Data storage directory
│   ├── reports/               # Generated PDF reports (.pdf)
│   └── uploads/               # User-uploaded Excel files (.xlsx)
├── automation/                # Core scraping & parsing logic
│   ├── __init__.py
│   ├── scraper.py             # Playwright browser automation & ddddocr CAPTCHA solver
│   ├── parser.py              # BeautifulSoup HTML result parser
│   └── excel_writer.py        # openpyxl Excel exporter with customized styling
├── backend/                   # FastAPI web server
│   ├── __init__.py
│   └── server.py              # REST API + WebSocket server + /api/report router mount
├── report_generator/          # AI PDF Report Generator Module
│   ├── __init__.py
│   ├── config.py              # Report design tokens, color palettes & typography configuration
│   ├── data_loader.py         # Loader for single/dual Excel files & in-memory records
│   ├── analytics_engine.py    # Multi-dimensional analytics computation engine
│   ├── chart_renderer.py     # Matplotlib high-resolution chart rendering pipeline
│   ├── ai_insights.py         # Heuristic natural language AI insight generator
│   ├── pdf_builder.py         # ReportLab document builder with custom page templates
│   ├── generate_report.py    # Orchestrator & CLI for PDF generation pipeline
│   ├── api.py                 # FastAPI router (`/api/report`) for upload, generate & download
│   ├── requirements.txt       # Report generator specific Python dependencies
│   └── report_sections/       # Modular section renderers (19 sections)
│       ├── cover_page.py
│       ├── table_of_contents.py
│       ├── executive_summary.py
│       ├── overall_statistics.py
│       ├── branch_analysis.py
│       ├── semester_analysis.py
│       ├── subject_analysis.py
│       ├── topper_analysis.py
│       ├── student_pages.py
│       ├── grade_distribution.py
│       ├── pass_percentage.py
│       ├── backlog_analysis.py
│       ├── heatmaps.py
│       ├── risk_analysis.py
│       ├── improvement_analysis.py
│       ├── comparison_analysis.py
│       ├── ai_insights_section.py
│       └── ai_recommendations.py
└── frontend/                  # React Vite SPA
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── .gitignore
    ├── .oxlintrc.json
    ├── dist/                  # Production build output (served by FastAPI)
    ├── public/
    └── src/
        ├── main.jsx           # React entry point
        ├── App.jsx            # Main scraper dashboard & batch runner (845+ lines)
        ├── App.css            # Component-level styles
        ├── ResultCompareStudio.jsx # Academic Comparison & PDF Parsing Studio (1430+ lines)
        └── index.css          # Global design system & theme variables (910+ lines)
```

---

## ✅ WHAT IS CURRENTLY IMPLEMENTED (Production Ready)

### 1. `automation/` — Web Scraping & Result Parsing Engine
- **`scraper.py` (`RGPVScraper`):**
  - Automated Playwright Chromium automation with sync API context manager.
  - Automatic selection of degree programs (B.Tech, B.Pharmacy, M.Tech, MCA, MBA) and target semesters.
  - Client-side JavaScript DOM listener monitoring ASP.NET postback state changes for fresh CAPTCHA loading.
  - Local AI CAPTCHA solving using `ddddocr` with string normalization (uppercase conversion, noise filter, and auto-refresh trigger on invalid characters).
  - Handles up to 12 auto-attempts per record with safe ASP.NET dialog/alert interceptors.
- **`parser.py`:**
  - Extracts student name (`#lblName`), SGPA (`#lblSGPA`), CGPA (`#lblcgpa`), and Result (`#lblResult`).
  - Fallback body text regex pattern extraction for non-standard layouts.
  - Dynamic subject grade table parser classifying fail grades (`F`, `FAIL`, `AB`, `ABSENT`, `RL`).
- **`excel_writer.py`:**
  - Generates `.xlsx` workbooks with blue headers (`DDEBF7`), auto-fitted columns, frozen headers (`A2`), and color-coded status cells (green PASS, red FAIL with subject breakdown).

### 2. `report_generator/` — Automatic AI PDF Report Generator
- **`analytics_engine.py`:** Computes high-level KPIs, grade distributions (A+, A, B, etc.), subject-wise pass/fail rates, branch comparison matrices, topper rankings, student at-risk flags, backlog heatmaps, and semester-over-semester improvement metrics.
- **`chart_renderer.py`:** Generates publication-ready Matplotlib charts saved as high-DPI temporary images:
  - SGPA distribution bar charts & histograms.
  - Pass/Fail circular donut charts.
  - Subject failure rate bar graphs.
  - Multi-semester SGPA box plots and trend lines.
  - Dual-dataset comparison radar/grouped bar charts.
- **`ai_insights.py`:** Rule-based AI narrative engine synthesizing qualitative executive summaries, strengths, weakness identification, and actionable academic recommendations.
- **`pdf_builder.py` & `report_sections/`:** Custom ReportLab canvas builder featuring cover pages, running headers/footers with dynamic page numbering, styled tables, embedded charts, table of contents, and individual student report card pages.
- **`api.py`:** Provides REST endpoints (`/api/report/upload`, `/api/report/generate`, `/api/report/download`, `/api/report/status`) integrated into `backend/server.py`.

### 3. `frontend/src/ResultCompareStudio.jsx` — Academic Comparison Suite
- **Multi-Mode Analytics:**
  1. **Class vs Class Comparison:** Side-by-side comparison of 2 Excel/CSV datasets analyzing average SGPA, pass %, total backlogs, top performers, best/weakest subjects, and grade distributions.
  2. **Student vs Student Comparison:** Direct grade comparison of two individual students across all subjects with difference indicators and AI summaries.
  3. **Semester over Semester Progress:** Tracks student cohort performance across semesters, identifying rank shifts, improved students (+0.05 SGPA), and declining students.
- **Dynamic File Processing:**
  - Upload drag-and-drop zones supporting `.xlsx`, `.csv`, and `.pdf` files.
  - In-browser PDF parsing using `pdf.js` with regex extraction for student result sheets.
  - In-browser Excel parsing via `XLSX` library.
  - Client-side PDF comparison report export via `jsPDF`.

### 4. `backend/server.py` — Unified FastAPI Server
- Integrated WebSocket manager (`ConnectionManager`) streaming live scraper progress and system logs (`WebLogger`).
- Threaded job orchestrator (`ScrapeJobRunner`) with global locking and execution controls (start/cancel).
- Embedded mounts for `report_router` (`/api/report`) and static asset serving for `frontend/dist`.

### 5. `Dockerfile` & Deployment Tooling
- Multi-stage Docker build combining Node 20 (Vite frontend compiler) and Python 3.10-slim runtime.
- System library dependencies installed for OpenCV, Pillow, and Playwright Chromium headless execution.
- `start.ps1` PowerShell script allowing seamless one-click local launches of both development/production ports.

---

## 🔌 API Reference (Implemented)

### Scraper API (`/api/scrape`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scrape/start` | Start bulk scraping job |
| `POST` | `/api/scrape/cancel` | Cancel running job |
| `GET` | `/api/scrape/status` | Get current job status dict |
| `GET` | `/api/scrape/download?path=...` | Download output Excel file |
| `WS` | `/api/ws` | WebSocket for real-time progress & terminal logs |

### Report Generator API (`/api/report`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/report/upload` | Upload binary Excel file to `data/uploads/` |
| `POST` | `/api/report/generate` | Trigger AI PDF report generation from dataset |
| `GET` | `/api/report/download?path=...` | Download generated PDF report |
| `GET` | `/api/report/status` | Query current PDF generation status |

---

## 🚀 HOW TO RUN

### Option 1: One-Click Launcher (Windows PowerShell)
```powershell
.\start.ps1
```
*Automatically builds frontend assets and launches FastAPI backend (`http://localhost:8000`) & Vite server (`http://localhost:5173`) in separate windows.*

### Option 2: Docker Containerization
```bash
# Build unified Docker image
docker build -t result-ai .

# Run container
docker run -p 8000:8000 result-ai
# Open http://localhost:8000 in your browser
```

### Option 3: Manual Local Development

#### 1. Backend Server
```powershell
# From project root
venv\Scripts\python -m uvicorn backend.server:app --reload --port 8000
```

#### 2. Frontend Server
```powershell
cd frontend
npm install
npm run dev
# Accessible at http://localhost:5173
```

#### 3. CLI Mode — Web Scraper
```powershell
venv\Scripts\python main.py --prefix 0105IT2410 --start 1 --end 20 --pad 2 --sem 3 --program B.Tech.
```

#### 4. CLI Mode — AI PDF Report Generator
```powershell
# Single dataset report
venv\Scripts\python -m report_generator.generate_report --input data/RGPV_Result_0105IT2410_1-20.xlsx --college "RGPV" --department "IT" --semester 3

# Dual dataset comparison report
venv\Scripts\python -m report_generator.generate_report --input data/sem4.xlsx --compare data/sem3.xlsx
```

---

## ⚠️ KNOWN LIMITATIONS & NOTES

1. **Single Scraper Job Lock:** Global `active_runner` lock permits one active scraping process at a time on single-node setups.
2. **In-Memory Job State:** Active job logs and status are maintained in-memory (`ScrapeJobRunner`). Restarting server clears active job progress history (persisted Excel output remains saved in `/data`).
3. **External Portal Dependency:** Selector structures (`#ctl00_ContentPlaceHolder1_...`) depend on RGPV portal layout stability.
4. **CAPTCHA Solving:** Uses local `ddddocr` engine in headless Chromium mode to prevent OS high-DPI scaling artifacts.

---

## 🗺️ PLANNED FUTURE ENHANCEMENTS

### Phase 1 — Persistence & Auth (Next Up)
- [ ] SQLite or PostgreSQL database backend (SQLAlchemy ORM).
- [ ] Role-Based Access Control (JWT Authentication for Admin/Faculty).
- [ ] Historical Job Records database persistence.

### Phase 2 — Distributed Infrastructure
- [ ] Celery + Redis distributed task queue for multi-worker scaling.
- [ ] Proxy pool rotation for high-volume scraping jobs.

### Phase 3 — Advanced AI & Notifications
- [ ] Custom CNN/OCR fine-tuned model on RGPV CAPTCHAs.
- [ ] WhatsApp / Email automated notification alerts on job completion.
