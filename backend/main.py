import sys
import os
import uuid
import asyncio # Ensure asyncio is imported
import pandas as pd # Added import
from datetime import datetime
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the root directory to sys.path to allow imports from trading_logic, etc.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import trading_logic
import performance_analyzer
import data_loader
# config_loader might not be directly used if API passes all config

# Define Data Directory relative to this file's location (backend/main.py)
# It should point to the 'data' folder in the project root
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Pydantic Models
class BacktestSettings(BaseModel):
    initial_capital: float
    markets: List[str]
    entry_donchian_period: int
    take_profit_long_exit_period: int
    take_profit_short_exit_period: int
    atr_period: int
    stop_loss_atr_multiplier: float
    risk_per_trade: float
    total_portfolio_risk_limit: float
    slippage_pips: float
    commission_per_lot: float
    pip_point_value: Dict[str, float]
    lot_size: Dict[str, int]
    max_units_per_market: Dict[str, int]

class JobCreationResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None

class EquityDataPoint(BaseModel):
    timestamp: datetime
    equity: float

class TradeLogEntry(BaseModel):
    # Using a more generic structure for now, can be refined
    order_id: Any
    symbol: Any
    action: Any
    quantity: Any
    price: Any
    timestamp: Any
    commission: Any
    slippage: Any
    realized_pnl: Optional[float] = None # Changed line
    type: Any # Could be 'entry', 'exit', 'stop_loss', etc.

class BacktestResultsResponse(BaseModel):
    job_id: str
    status: str
    results: Optional[Dict[str, Any]] = None # For KPIs
    equity_curve: Optional[List[EquityDataPoint]] = None
    trade_log: Optional[List[TradeLogEntry]] = None
    message: Optional[str] = None

# Pydantic Models for Data Collection API
class DataCollectionRequest(BaseModel): # Ensure this model is defined or imported
    symbol: str
    startYear: int
    startMonth: int
    endYear: int
    endMonth: int
    apiKey: Optional[str] = None # Assuming API key might be optional or handled differently

class FileInfo(BaseModel):
    name: str
    size: int # size in bytes
    created_at: datetime # creation timestamp

class FileListResponse(BaseModel):
    files: List[FileInfo]
    total_files: int

# Job Store
job_store: Dict[str, Dict[str, Any]] = {}


async def run_backtest_task(job_id: str, settings_dict: dict):
    """
    Background task to run the backtest, calculate KPIs, and store results.
    """
    try:
        job_store[job_id]["status"] = "running"

        # Configuration Preparation
        # settings_dict itself is used as config_dict_for_run as it contains all necessary fields
        config_dict_for_run = settings_dict.copy() # Use a copy to avoid modifying the original settings

        # Data Loading
        # Path adjusted to be relative to the backend/main.py file,
        # assuming historical_data.csv is in the project root.
        raw_data_df = data_loader.load_csv_data('historical_data.csv')

        if raw_data_df.empty:
            raise ValueError("Loaded data is empty.")

        if not isinstance(raw_data_df.index, pd.DatetimeIndex):
            raise ValueError("Data does not have a DatetimeIndex. 'Timestamp' column might be missing or not set as index.")

        required_columns = ['Open', 'High', 'Low', 'Close'] # Define essential columns
        missing_columns = [col for col in required_columns if col not in raw_data_df.columns]
        if missing_columns:
            raise ValueError(f"Missing essential data columns: {', '.join(missing_columns)}")

        # Prepare historical_data_dict as expected by run_strategy
        # Assigning the loaded DataFrame to the first market specified.
        # This assumes a single CSV for one market or that run_strategy can handle it.
        historical_data_dict = {}
        if not config_dict_for_run.get("markets"):
            raise ValueError("Markets list is empty in settings.")

        # For now, assume the CSV is for the first market, or it's a general CSV
        # that trading_logic can use/filter. If multiple CSVs per market are needed,
        # data_loader and this section would need significant changes.
        # The prompt states: "assigning the loaded DataFrame to the first market specified in settings_dict["markets"]"
        first_market = config_dict_for_run["markets"][0]
        historical_data_dict[first_market] = raw_data_df

        # Execute Backtest
        # emergency_stop_activated is defaulted to False
        backtest_engine_results = trading_logic.run_strategy(
            historical_data_dict=historical_data_dict, # Changed keyword
            initial_capital=config_dict_for_run["initial_capital"],
            config=config_dict_for_run, # Pass the whole settings_dict as config
            emergency_stop_activated=False
        )

        # Calculate KPIs
        # risk_free_rate defaults to 0.0 if not in config
        risk_free_rate = config_dict_for_run.get('risk_free_rate', 0.0)
        kpi_results_dict = performance_analyzer.calculate_all_kpis(
            backtest_results=backtest_engine_results,
            config=config_dict_for_run, # Pass the whole settings_dict as config
            risk_free_rate_annual=risk_free_rate # Changed keyword
        )

        # Store Results
        job_store[job_id].update({
            "status": "completed",
            "kpis": kpi_results_dict,
            "equity_curve": backtest_engine_results.get("equity_curve"), # Stored as list of tuples
            "trade_log": backtest_engine_results.get("trade_log"),
            "error_message": None
        })

    except Exception as e:
        job_store[job_id].update({
            "status": "failed",
            "error_message": str(e),
            "kpis": None,
            "equity_curve": None,
            "trade_log": None
        })

async def run_datacollection_task(job_id: str, request_params: dict):
    """
    Background task to simulate data collection.
    """
    try:
        job_store[job_id]["status"] = "running"
        # Simulate data collection work
        await asyncio.sleep(5) # Simulate I/O bound operation
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["message"] = "Data collection finished."
    except Exception as e:
        job_store[job_id].update({
            "status": "failed",
            "message": str(e)
        })

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/backtest/run", status_code=202)
async def create_backtest_job(settings: BacktestSettings, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job_store[job_id] = {
        "status": "pending",
        "parameters": settings.model_dump(),
        "kpis": None,
        "equity_curve": None,
        "trade_log": None,
        "error_message": None,
        "message": "Job initiated." # Optional: a more descriptive initial message
    }
    background_tasks.add_task(run_backtest_task, job_id, settings.model_dump())
    return JobCreationResponse(job_id=job_id)

@app.post("/api/data/collect", response_model=JobCreationResponse, status_code=202)
async def start_data_collection(request: DataCollectionRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job_store[job_id] = {
        "status": "pending",
        "type": "data_collection", # Differentiate from backtest jobs
        "parameters": request.model_dump(),
        "message": "Data collection job initiated."
    }
    background_tasks.add_task(run_datacollection_task, job_id, request.model_dump())
    return JobCreationResponse(job_id=job_id)


@app.get("/api/backtest/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job["status"]
    message = None

    if status == "failed":
        message = job.get("error_message", "An unknown error occurred.")
    elif status == "completed":
        message = "Job completed successfully."
    elif status == "pending":
        message = job.get("message", "Job is pending.") # Use initial message if available
    elif status == "running":
        message = "Job is currently running."

    return JobStatusResponse(job_id=job_id, status=status, message=message)


@app.get("/api/backtest/results/{job_id}", response_model=BacktestResultsResponse)
async def get_job_results(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job["status"]

    if status == "completed":
        raw_equity_curve = job.get("equity_curve")
        converted_equity_curve = None
        if raw_equity_curve:
            converted_equity_curve = [
                EquityDataPoint(timestamp=item[0], equity=item[1]) for item in raw_equity_curve
            ]

        # Assuming TradeLogEntry is Dict[str, Any] or compatible with job.get("trade_log") items
        return BacktestResultsResponse(
            job_id=job_id,
            status="completed",
            results=job.get("kpis"),
            equity_curve=converted_equity_curve,
            trade_log=job.get("trade_log")
        )
    elif status in ["pending", "running"]:
        return BacktestResultsResponse(
            job_id=job_id,
            status=status,
            message=f"Backtest is {status}. Please try again later."
        )
    elif status == "failed":
        return BacktestResultsResponse(
            job_id=job_id,
            status="failed",
            message=job.get("error_message", "An unknown error occurred.")
        )
    else:
        # Should not happen with current states, but good for robustness
        raise HTTPException(status_code=500, detail=f"Unknown job status: {status}")


@app.websocket("/api/data/stream_log/{job_id}")
async def stream_log(websocket: WebSocket, job_id: str):
    await websocket.accept()

    job_info = job_store.get(job_id)
    if not job_info or job_info.get("type") != "data_collection":
        await websocket.send_text(f"ERROR: Job ID {job_id} not found or is not a data collection job.")
        await websocket.close(code=1008) # Policy Violation
        return

    await websocket.send_text(f"Streaming logs for data collection job {job_id}...")

    try:
        # Loop to send log messages based on job status
        for i in range(10): # Simulate sending 10 log lines as per example
            current_job_info = job_store.get(job_id) # Fetch fresh status
            if not current_job_info:
                await websocket.send_text(f"ERROR: Job {job_id} disappeared unexpectedly.")
                break

            status = current_job_info["status"]

            if status == "running":
                await websocket.send_text(f"LOG: Line {i+1} for job {job_id} (Status: {status})")
                await asyncio.sleep(1)  # Wait 1 second
            elif status == "completed":
                await websocket.send_text(f"INFO: Job {job_id} completed. {current_job_info.get('message', '')}")
                break
            elif status == "failed":
                await websocket.send_text(f"ERROR: Job {job_id} failed. {current_job_info.get('message', '')}")
                break
            elif status == "pending":
                 await websocket.send_text(f"INFO: Job {job_id} is pending. Waiting for it to start...")
                 await asyncio.sleep(1) # Wait for job to start
            else: # unknown status or job disappeared
                await websocket.send_text(f"INFO: Job {job_id} status is {status}. Ending log stream.")
                break

        # After loop, or if job completes/fails during loop
        final_job_info = job_store.get(job_id, {})
        final_status = final_job_info.get("status", "unknown")
        final_message = final_job_info.get("message", "")
        await websocket.send_text(f"INFO: Log streaming ended for job {job_id}. Final status: {final_status}. Message: {final_message}")

    except WebSocketDisconnect:
        print(f"Client disconnected from job {job_id} log stream.")  # Server-side log
    except Exception as e:
        error_message = f"ERROR: An error occurred during log streaming: {str(e)}"
        print(f"Error in log streaming for job {job_id}: {e}")  # Server-side log
        try:
            await websocket.send_text(error_message)
        except Exception:  # Handle cases where sending error also fails
            pass  # e.g., connection already closed
    finally:
        # FastAPI handles closing the WebSocket connection automatically when the function exits
        # or an unhandled exception occurs. Explicit websocket.close() can be used if specific
        # close codes or reasons are needed before this point.
        print(f"Closing WebSocket connection for job {job_id}")


@app.get("/api/data/files", response_model=FileListResponse)
async def list_data_files():
    found_files = []
    if not os.path.exists(DATA_DIR) or not os.path.isdir(DATA_DIR):
        # Log this situation server-side, though client gets an empty list as per requirement
        print(f"Data directory {DATA_DIR} not found or is not a directory.")
        return FileListResponse(files=[], total_files=0)

    try:
        for f_name in os.listdir(DATA_DIR):
            file_path = os.path.join(DATA_DIR, f_name)
            # Check if it's a file and ends with .csv (case-insensitive)
            if os.path.isfile(file_path) and f_name.lower().endswith('.csv'):
                try:
                    size = os.path.getsize(file_path)
                    created_at_timestamp = os.path.getctime(file_path)
                    created_at_datetime = datetime.fromtimestamp(created_at_timestamp)

                    file_info = FileInfo(
                        name=f_name,
                        size=size,
                        created_at=created_at_datetime
                    )
                    found_files.append(file_info)
                except OSError as e:
                    # Log error for specific file, but continue with others
                    print(f"Error processing file {file_path}: {e}")

        return FileListResponse(files=found_files, total_files=len(found_files))

    except OSError as e:
        # Log error for directory listing issue
        print(f"Error listing files in directory {DATA_DIR}: {e}")
        # As per requirement, could return empty list or raise HTTP 500
        # Returning empty list for now to prevent full endpoint failure on partial read issues.
        # For a more robust solution, an HTTP 500 might be better if any OS error occurs.
        raise HTTPException(status_code=500, detail=f"Server error accessing data files: {str(e)}")
