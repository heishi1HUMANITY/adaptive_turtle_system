Write-Host "Starting backend server..."
# Command to execute uvicorn. Might need `python -m uvicorn` depending on PATH setup.
# Using `uvicorn` directly for now.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
