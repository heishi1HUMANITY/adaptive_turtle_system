#!/bin/bash
echo "Installing backend dependencies..."
pip install -r requirements.txt

# Exit if pip install failed
if [ $? -ne 0 ]; then
    echo "Failed to install backend dependencies. Exiting."
    exit 1
fi

echo "Starting backend server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
