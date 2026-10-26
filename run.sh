#!/bin/bash
echo "============================================"
echo "  UniAssist - AI Student Support Chatbot"
echo "============================================"

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run ingestion if index is missing
if [ ! -d "chroma_db" ]; then
    echo ""
    echo "Running knowledge base ingestion..."
    python scripts/ingest.py
    echo ""
fi

echo "Starting server at http://localhost:8000"
echo "Admin panel: http://localhost:8000/admin"
echo "API docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
