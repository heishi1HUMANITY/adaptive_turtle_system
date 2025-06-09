# Backend API

This directory contains the backend API for the application, built with FastAPI.

## Setup and Running

### 1. Install Dependencies

Navigate to the `backend` directory and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Start the Development Server

Once the dependencies are installed, you can start the FastAPI development server using Uvicorn:

```bash
uvicorn main:app --reload
```

This command will start the server, typically at `http://localhost:8000`. The `--reload` flag enables auto-reloading when code changes are detected.

The API includes an endpoint `/api/health` which can be used to check if the server is running and accessible. It should return `{"status": "ok"}`.
