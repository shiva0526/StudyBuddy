#!/bin/bash

echo "Starting StudyBuddy..."
echo "Backend API: http://localhost:8000"
echo "Frontend: http://localhost:5000"
echo ""

python start_backend.py &
BACKEND_PID=$!

cd frontend
npm run dev &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
