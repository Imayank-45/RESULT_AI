"""
api.py
------
FastAPI router for the AI Report Generator.

Provides endpoints for report generation and download.
This router can be optionally mounted by the main backend server:

    from report_generator.api import report_router
    app.include_router(report_router, prefix="/api/report")

NOTE: This does NOT modify the existing server.py.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from report_generator.generate_report import generate_report
from backend.db.auth import get_current_user
from backend.db.models import User


# ═══════════════════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════════════════

report_router = APIRouter(tags=["Report Generator"])


class ReportRequest(BaseModel):
    """Request schema for report generation."""
    excel_path: str
    compare_path: Optional[str] = None
    college_name: str = "Rajiv Gandhi Proudyogiki Vishwavidyalaya"
    department: str = "Department of Information Technology"
    semester: str = ""
    program: str = "B.Tech."
    job_id: str = ""
    max_student_pages: Optional[int] = 100


class ReportResponse(BaseModel):
    """Response schema for report generation."""
    status: str
    report_path: str
    message: str


# Track report generation status
_report_status = {"generating": False, "last_path": None, "error": None}
_report_lock = threading.Lock()


@report_router.post("/upload")
async def upload_excel_file(request: Request, filename: str, current_user: User = Depends(get_current_user)):
    """Upload raw binary Excel file content and save it to data/uploads/."""
    upload_dir = os.path.join("data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Read raw body bytes
    body = await request.body()
    
    # Security: sanitize filename to prevent path traversal
    safe_name = os.path.basename(filename)
    file_path = os.path.join(upload_dir, safe_name)
    
    with open(file_path, "wb") as f:
        f.write(body)
        
    return {"excel_path": f"data/uploads/{safe_name}"}


@report_router.post("/generate", response_model=ReportResponse)
def generate_report_endpoint(req: ReportRequest, current_user: User = Depends(get_current_user)):
    """Generate a PDF report from the specified Excel file."""
    global _report_status

    with _report_lock:
        if _report_status["generating"]:
            raise HTTPException(status_code=400, detail="A report is already being generated.")

    # Validate input
    if not os.path.exists(req.excel_path):
        # Try relative to project root
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alt_path = os.path.join(script_dir, req.excel_path)
        if os.path.exists(alt_path):
            req.excel_path = alt_path
        else:
            raise HTTPException(status_code=404, detail=f"Excel file not found: {req.excel_path}")

    with _report_lock:
        _report_status["generating"] = True
        _report_status["error"] = None

    try:
        output_path = generate_report(
            input_path=req.excel_path,
            compare_path=req.compare_path,
            college_name=req.college_name,
            department=req.department,
            semester=req.semester,
            program=req.program,
            job_id=req.job_id,
            max_student_pages=req.max_student_pages,
        )

        with _report_lock:
            _report_status["generating"] = False
            _report_status["last_path"] = output_path

        return ReportResponse(
            status="completed",
            report_path=output_path,
            message=f"Report generated successfully: {output_path}"
        )
    except Exception as e:
        with _report_lock:
            _report_status["generating"] = False
            _report_status["error"] = str(e)

        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@report_router.get("/download")
def download_report(path: str):
    """Download a generated PDF report."""
    if not path.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Security: only allow files from data/reports
    base = os.path.basename(path)
    safe_path = os.path.join("data", "reports", base)

    if not os.path.exists(safe_path):
        # Try absolute path
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alt_path = os.path.join(script_dir, "data", "reports", base)
        if os.path.exists(alt_path):
            safe_path = alt_path
        else:
            raise HTTPException(status_code=404, detail="Report file not found.")

    return FileResponse(
        path=safe_path,
        filename=base,
        media_type="application/pdf"
    )


@report_router.get("/status")
def get_report_status():
    """Get current report generation status."""
    return _report_status
