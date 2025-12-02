#!/bin/bash
# Script to start the Gap Assessment API server

echo "=" | head -c 80
echo ""
echo "Starting Gap Assessment API Server"
echo "=" | head -c 80
echo ""

# Activate virtual environment
source .venv/bin/activate

# Start server
echo "Starting server on http://localhost:8000"
echo ""
echo "API Endpoints:"
echo "  - GET  http://localhost:8000/health"
echo "  - GET  http://localhost:8000/status"
echo "  - POST http://localhost:8000/assess  (Main endpoint)"
echo "  - GET  http://localhost:8000/logs/summary"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn api.gap_assessment_api:app --host 0.0.0.0 --port 8000

