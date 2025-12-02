#!/bin/bash

echo "=========================================="
echo "Starting Gap Assessment Frontend"
echo "=========================================="

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

echo ""
echo "Starting development server..."
echo "Frontend will be available at: http://localhost:3000"
echo "Make sure the backend API is running at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="

npm run dev

