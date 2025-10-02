#!/bin/bash
# Start the Neunet backend server

echo "Starting Neunet Backend on http://localhost:8000"
echo "API Documentation available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
