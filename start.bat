@echo off
echo ======================================
echo    StudyMate AI - Starting Server
echo ======================================

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [WARN] No venv found - using system Python
)

REM Create uploads directory
if not exist uploads\vectors mkdir uploads\vectors
echo [OK] Upload directories ready

REM Start the server
echo [INFO] Starting FastAPI server on http://localhost:8000
echo [INFO] API docs at http://localhost:8000/api/docs
echo.
python -m backend.main

pause
