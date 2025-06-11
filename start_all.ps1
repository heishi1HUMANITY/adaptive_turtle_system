Write-Host "Starting all services..."

# Start the backend in a new PowerShell window
Write-Host "Starting backend server in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Backend Output:'; cd backend; .\start_backend.ps1"

# Wait a few seconds for the backend to initialize (optional)
Write-Host "Waiting for backend to initialize (3 seconds)..."
Start-Sleep -Seconds 3

# Start the frontend in a new PowerShell window
Write-Host "Starting frontend development server in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Frontend Output:'; cd frontend; .\start_frontend.ps1"

Write-Host "Backend and Frontend servers have been started in separate windows."
Write-Host "To stop them, close their respective PowerShell windows."
