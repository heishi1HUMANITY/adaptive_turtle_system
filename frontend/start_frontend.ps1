Write-Host "Installing frontend dependencies..."
npm install

# Check if npm install failed
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install frontend dependencies. Exiting."
    exit 1
}

Write-Host "Starting frontend development server..."
# Assumes npm is in PATH.
# The script should be run from within the 'frontend' directory or it should cd into it.
# For simplicity, this script assumes it's run from `frontend\` or `Set-Location frontend; .\start_frontend.ps1`
npm start
