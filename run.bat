@echo off
echo ============================================
echo   UniAssist - AI Student Support Chatbot
echo ============================================

REM Activate venv if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run ingestion if index is missing
if not exist "chroma_db" (
    echo.
    echo Running knowledge base ingestion...
    python scripts/ingest.py
    echo.
)

echo Starting server at http://localhost:8000
echo Admin panel: http://localhost:8000/admin
echo API docs: http://localhost:8000/docs
echo Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
