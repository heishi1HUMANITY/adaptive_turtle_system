#!/bin/bash
echo "Installing frontend dependencies..."
npm install

# Exit if npm install failed
if [ $? -ne 0 ]; then
    echo "Failed to install frontend dependencies. Exiting."
    exit 1
fi

echo "Starting frontend development server..."
# Ensure we are in the frontend directory context if the script is called from elsewhere.
# However, standard practice is to call it from within its directory or provide full path.
# For simplicity, assuming it's run from `frontend/` or `cd frontend && ./start_frontend.sh`
npm start
