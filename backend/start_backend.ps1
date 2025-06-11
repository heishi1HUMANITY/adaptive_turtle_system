Write-Host "Installing backend dependencies..."
pip install -r requirements.txt

# Check if pip install failed
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install backend dependencies. Exiting."
    exit 1
}

Write-Host "Starting backend server..."
# Command to execute uvicorn. Might need `python -m uvicorn` depending on PATH setup.
# Using `uvicorn` directly for now.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
