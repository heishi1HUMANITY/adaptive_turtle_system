#!/bin/bash

echo "Starting all services..."

# Start the backend in the background
echo "Starting backend server in the background..."
(cd backend && ./start_backend.sh) &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"

# Wait a few seconds for the backend to initialize (optional, but can be helpful)
sleep 3

# Start the frontend in the foreground (or background if preferred)
echo "Starting frontend development server..."
# If you want to run frontend in background too, add '&' and manage its PID
(cd frontend && ./start_frontend.sh)

# Note: If frontend is in foreground, this script will remain active until frontend is stopped.
# If both are in background, the script would exit, and users would need to manage processes separately.

echo "To stop the backend server, run: kill $BACKEND_PID"
echo "To stop the frontend server, press Ctrl+C in its terminal (if in foreground) or find and kill its process."
