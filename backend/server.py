# server.py
import asyncio
import io
import os
import queue
import sys
import threading
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys
# Add parent directory to sys.path to resolve automation module import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing modules
from automation.scraper import RGPVScraper
from automation.parser import parse_result_html, ResultNotFound
from automation.excel_writer import write_excel
from report_generator.api import report_router

# Import Database & Auth modules
from backend.db.database import Base, engine, SessionLocal
from backend.db.models import User
from backend.db.auth import get_password_hash, get_current_user
from backend.auth_router import auth_router

# Initialize FastAPI
app = FastAPI(title="ResultAI API", version="1.0.0")

# Mount Routers
app.include_router(auth_router)
app.include_router(report_router, prefix="/api/report")

# Enable CORS for frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
update_queue = queue.Queue()
active_runner: Optional['ScrapeJobRunner'] = None
runner_lock = threading.Lock()
last_job_status: Optional[dict] = None
background_tasks = set()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# WebLogger captures standard output and streams it to the web UI
class WebLogger(io.TextIOBase):
    def __init__(self, original_stdout, log_callback):
        self.original_stdout = original_stdout
        self.log_callback = log_callback
        self._line_buffer = ""

    def write(self, s):
        self.original_stdout.write(s)
        self.original_stdout.flush()
        self._line_buffer += s
        if "\n" in self._line_buffer:
            lines = self._line_buffer.split("\n")
            for line in lines[:-1]:
                clean_line = line.strip()
                if clean_line:
                    self.log_callback(clean_line)
            self._line_buffer = lines[-1]
        return len(s)

    def flush(self):
        self.original_stdout.flush()

def log_callback(line: str):
    global active_runner
    if active_runner:
        active_runner.logs.append(line)
        # Only keep last 500 logs to conserve memory
        if len(active_runner.logs) > 500:
            active_runner.logs.pop(0)
    update_queue.put({"type": "log", "message": line})

# Redirect sys.stdout to our custom logger
original_stdout = sys.stdout
sys.stdout = WebLogger(original_stdout, log_callback)

class ScrapeJobRunner:
    def __init__(self, prefix: str, start: int, end: int, pad: int, sem: Optional[str], program: str, headless: bool = True):
        self.prefix = prefix
        self.start = start
        self.end = end
        self.pad = pad
        self.sem = sem
        self.program = program
        self.headless = headless
        
        self.status = "running"
        self.total = end - start + 1
        self.processed = 0
        self.records = []
        self.logs = []
        self.pass_count = 0
        self.fail_count = 0
        self.not_found_count = 0
        self.error_count = 0
        self.current_enrollment = ""
        self.excel_file_path = None
        
        self._cancel_requested = False
        self._scraper = None
        self._thread = None

    def start_job(self):
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def cancel(self):
        self._cancel_requested = True
        print("[System] Cancellation requested. Stopping scraper and closing browser...")
        if self._scraper:
            try:
                # Force browser closure if active
                if self._scraper._browser:
                    self._scraper._browser.close()
            except Exception as e:
                print(f"[System] Error closing browser: {e}")
        self.status = "cancelled"
        self.notify_progress()

    def notify_progress(self):
        update_queue.put({
            "type": "status",
            "data": self.get_status_dict()
        })

    def get_status_dict(self):
        return {
            "status": self.status,
            "total": self.total,
            "processed": self.processed,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "not_found_count": self.not_found_count,
            "error_count": self.error_count,
            "current_enrollment": self.current_enrollment,
            "excel_file_path": self.excel_file_path,
            "records": self.records,
            "logs": self.logs
        }

    def _run(self):
        print(f"\n[System] Starting bulk fetch: Prefix={self.prefix}, Range={self.start}-{self.end}, Sem={self.sem or 'All'}, Program={self.program}")
        self.notify_progress()
        
        try:
            self._scraper = RGPVScraper(headless=self.headless)
            with self._scraper as scraper:
                for roll in range(self.start, self.end + 1):
                    if self._cancel_requested:
                        self.status = "cancelled"
                        break

                    enrollment = f"{self.prefix}{str(roll).zfill(self.pad)}"
                    self.current_enrollment = enrollment
                    self.notify_progress()

                    print(f"\n[Scraper] Fetching {enrollment} ({roll - self.start + 1}/{self.total})...")
                    fetch_result = scraper.fetch_result_html(enrollment, sem=self.sem, program=self.program)

                    if self._cancel_requested:
                        self.status = "cancelled"
                        break

                    if fetch_result.error:
                        if "browser closed" in fetch_result.error.lower() or "closed by user" in fetch_result.error.lower():
                            self.status = "cancelled"
                            print("[System] Browser was closed by user. Terminating job...")
                            break
                        
                        print(f"[{enrollment}] Fetch failed: {fetch_result.error}")
                        self.records.append({"enrollment": enrollment, "not_found": True})
                        self.error_count += 1
                        self.processed += 1
                        self.notify_progress()
                        continue

                    try:
                        record = parse_result_html(fetch_result.html, enrollment)
                        self.records.append(record)
                        if record["result"] == "PASS":
                            self.pass_count += 1
                        elif record["result"] == "FAIL":
                            self.fail_count += 1
                        print(f"[{enrollment}] Success: Result={record['result']} | SGPA={record['sgpa']} | CGPA={record['cgpa']}")
                    except ResultNotFound:
                        print(f"[{enrollment}] No result record found.")
                        self.records.append({"enrollment": enrollment, "not_found": True})
                        self.not_found_count += 1
                    except Exception as e:
                        print(f"[{enrollment}] Error parsing HTML: {e}")
                        self.records.append({"enrollment": enrollment, "not_found": True})
                        self.error_count += 1

                    self.processed += 1
                    self.notify_progress()

            if not self._cancel_requested and self.status == "running":
                print("\n[System] Compiling results to Excel spreadsheet...")
                os.makedirs("data", exist_ok=True)
                out_path = f"data/RGPV_Result_{self.prefix}_{self.start}-{self.end}.xlsx"
                write_excel(self.records, out_path)
                self.excel_file_path = out_path
                self.status = "completed"
                print(f"[System] Job finished successfully! Excel file saved to: {out_path}")
        except Exception as e:
            self.status = "failed"
            print(f"[System] Critical error occurred: {e}")
        finally:
            self.current_enrollment = ""
            self.notify_progress()
            # Save status to global cache to preserve it
            global last_job_status
            last_job_status = self.get_status_dict()
            # Release runner lock
            global active_runner
            with runner_lock:
                active_runner = None


# API Schemas
class StartJobRequest(BaseModel):
    prefix: str
    start: int
    end: int
    pad: int = 2
    sem: Optional[str] = None
    program: str = "B.Tech."
    headless: bool = True


@app.post("/api/scrape/start")
def start_scraping_job(req: StartJobRequest, current_user: User = Depends(get_current_user)):
    global active_runner
    with runner_lock:
        if active_runner is not None:
            raise HTTPException(status_code=400, detail="A scraping job is already running.")
        
        if req.start > req.end:
            raise HTTPException(status_code=400, detail="Start roll number must be less than or equal to end roll number.")

        active_runner = ScrapeJobRunner(
            prefix=req.prefix,
            start=req.start,
            end=req.end,
            pad=req.pad,
            sem=req.sem,
            program=req.program,
            headless=req.headless
        )
        active_runner.start_job()
        
    return {"message": "Scraping job started successfully.", "job": active_runner.get_status_dict()}


@app.post("/api/scrape/cancel")
def cancel_scraping_job(current_user: User = Depends(get_current_user)):
    global active_runner
    if active_runner is None:
        raise HTTPException(status_code=400, detail="No active scraping job is running.")
    
    active_runner.cancel()
    return {"message": "Job cancellation triggered."}


@app.get("/api/scrape/status")
def get_scraping_status():
    global active_runner, last_job_status
    if active_runner is None:
        if last_job_status:
            return last_job_status
        return {
            "status": "idle",
            "total": 0,
            "processed": 0,
            "pass_count": 0,
            "fail_count": 0,
            "not_found_count": 0,
            "error_count": 0,
            "current_enrollment": "",
            "excel_file_path": None,
            "records": [],
            "logs": []
        }
    return active_runner.get_status_dict()


@app.get("/api/scrape/download")
def download_excel_file(path: str):
    base_name = os.path.basename(path)
    if not base_name.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file extension. Only Excel files are supported.")
    
    # Ensure file exists in data directory
    full_path = os.path.join("data", base_name)
    if not os.path.exists(full_path):
        # Try fallback relative to script parent directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fallback_path = os.path.join(script_dir, "data", base_name)
        if os.path.exists(fallback_path):
            full_path = fallback_path
        else:
            raise HTTPException(status_code=404, detail="Requested Excel file was not found.")
    
    return FileResponse(
        path=full_path, 
        filename=base_name, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# WebSocket communication loop
async def broadcast_updates():
    while True:
        while not update_queue.empty():
            try:
                message = update_queue.get_nowait()
                await manager.broadcast(message)
            except queue.Empty:
                break
        await asyncio.sleep(0.15)


# WebSocket endpoint
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial status
    global active_runner, last_job_status
    if active_runner:
        await websocket.send_json({"type": "status", "data": active_runner.get_status_dict()})
    elif last_job_status:
        await websocket.send_json({"type": "status", "data": last_job_status})
    else:
        await websocket.send_json({"type": "status", "data": {
            "status": "idle",
            "total": 0,
            "processed": 0,
            "pass_count": 0,
            "fail_count": 0,
            "not_found_count": 0,
            "error_count": 0,
            "current_enrollment": "",
            "excel_file_path": None,
            "records": [],
            "logs": []
        }})
        
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Start DB initialization and background broadcast task on startup
@app.on_event("startup")
async def startup_event():
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    
    # Seed default admin user if database is empty or update admin credentials
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == "admin@resultai.com").first()
        if not admin_user:
            default_admin = User(
                name="Administrator",
                email="admin@resultai.com",
                password_hash=get_password_hash("Admin@123456"),
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print("[System] Default admin user seeded: admin@resultai.com / Admin@123456")
        else:
            admin_user.password_hash = get_password_hash("Admin@123456")
            admin_user.is_active = True
            db.commit()
            print("[System] Default admin password synced: admin@resultai.com / Admin@123456")
    except Exception as e:
        print(f"[System] Database startup initialization error: {e}")
    finally:
        db.close()
    # Copy brand logo artifact to frontend folders
    try:
        import shutil
        logo_artifact = r"C:\Users\mayan\.gemini\antigravity-ide\brain\14285cfe-ce6a-4f14-b649-95f140bfe626\media__1784561737544.jpg"
        if os.path.exists(logo_artifact):
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            public_dir = os.path.join(root_dir, "frontend", "public")
            src_assets = os.path.join(root_dir, "frontend", "src", "assets")
            dist_dir = os.path.join(root_dir, "frontend", "dist")
            
            for d in [public_dir, src_assets, dist_dir]:
                os.makedirs(d, exist_ok=True)
                shutil.copy(logo_artifact, os.path.join(d, "logo.png"))
                shutil.copy(logo_artifact, os.path.join(d, "logo.jpg"))
            
            import base64
            with open(logo_artifact, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            js_content = f'export const LOGO_BASE64 = "data:image/jpeg;base64,{b64}";\nexport default LOGO_BASE64;\n'
            with open(os.path.join(src_assets, "logoData.js"), "w", encoding="utf-8") as f:
                f.write(js_content)

            print("[System] Official ResultAI brand logo copied & logoData.js created!")
    except Exception as exc:
        print(f"[System] Logo sync warning: {exc}")

    task = asyncio.create_task(broadcast_updates())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


# Serve static frontend files if built
frontend_dist_path = "frontend/dist"
if not os.path.exists(frontend_dist_path):
    # Try parent directory relative to script
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_path = os.path.join(script_dir, "frontend", "dist")
    if os.path.exists(fallback_path):
        frontend_dist_path = fallback_path

if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static")
else:
    @app.get("/")
    def read_root():
        return {
            "message": "ResultAI Backend API is running successfully.",
            "frontend_instructions": "To view the user interface, run Vite developer server in '/frontend' folder or run 'npm run build' inside '/frontend' to serve statically.",
            "api_doc": "/docs"
        }


if __name__ == "__main__":
    import uvicorn
    # Start the server (will run on http://localhost:8000)
    uvicorn.run(app, host="127.0.0.1", port=8000)
