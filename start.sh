#!/bin/bash
echo "======================================"
echo "   StudyMate AI - Starting Server"
echo "======================================"

# Activate virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "[OK] Virtual environment activated"
else
    echo "[WARN] No venv found - using system Python"
fi

# Create upload directories
mkdir -p uploads/vectors
echo "[OK] Upload directories ready"

# Start the server
echo "[INFO] Starting FastAPI server on http://localhost:8000"
echo "[INFO] API docs at http://localhost:8000/api/docs"
echo ""
python -m backend.main
