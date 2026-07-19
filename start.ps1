# start.ps1 - ResultAI: Frontend + Backend dono ek saath start karo

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_PYTHON = Join-Path $ROOT "venv\Scripts\python.exe"
$SERVER_SCRIPT = Join-Path $ROOT "backend\server.py"
$FRONTEND_DIR = Join-Path $ROOT "frontend"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   ResultAI - Starting Frontend and Backend" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Start Backend in a new window ---
Write-Host "[1/2] Starting Backend (FastAPI on localhost:8000)..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title ResultAI Backend && `"$VENV_PYTHON`" `"$SERVER_SCRIPT`""

Start-Sleep -Seconds 3

# --- Start Frontend in a new window ---
Write-Host "[2/2] Starting Frontend (Vite on localhost:5173)..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title ResultAI Frontend && cd /d `"$FRONTEND_DIR`" && npm run dev"

Write-Host ""
Write-Host "Both servers launched in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend  : http://localhost:8000"      -ForegroundColor Cyan
Write-Host "  Frontend : http://localhost:5173"      -ForegroundColor Cyan
Write-Host "  API Docs : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
