import sys
import os
import uuid
import asyncio # Ensure asyncio is imported
import time # Import time module
import threading # Add threading import
import pandas as pd # Added import
from datetime import datetime
from typing import List, Dict, Optional, Any
import subprocess # Added import
import sys # Added import

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
            "error_message": None,
            "message": "Backtest completed successfully." # Added success message
        })

    except Exception as e:
        error_str = str(e)
        job_store[job_id].update({
            "status": "failed",
            "error_message": error_str,
            "message": f"Backtest failed: {error_str}", # Added failure message
            "kpis": None,
            "equity_curve": None,
            "trade_log": None
        })

def _blocking_data_collection_simulation(request_params: dict) -> Dict[str, Any]:
    """
    Synchronous function to perform actual data collection by calling collect_data.py.
    Returns a dictionary with status and message.
    """
    status_updates = []
    output_filepath = None
    # Default to failure until success is explicitly determined
    final_status = "failed"
    final_message = "Data collection process did not start or encountered an unexpected issue."

    try:
        symbol = request_params.get("symbol")
        req_start_year = request_params.get("startYear")
        req_start_month = request_params.get("startMonth")
        req_end_year = request_params.get("endYear")
        req_end_month = request_params.get("endMonth")
        api_key = request_params.get("apiKey")

        if not api_key:
            return {"status": "failed", "message": "API key is missing."}

        if not all([symbol, req_start_year, req_start_month, req_end_year, req_end_month]):
            return {"status": "failed", "message": "Missing required parameters for data collection (symbol, start/end year/month)."}

        script_dir = os.path.dirname(__file__)
        project_root = os.path.join(script_dir, '..')
        collect_data_script_path = os.path.join(project_root, 'collect_data.py')

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            status_updates.append(f"Created data directory: {DATA_DIR}")

        # --- Call collect_data.py (once) ---
        status_updates.append(f"Attempting to fetch full timeseries data for {symbol} using collect_data.py...")
        print(f"Running collect_data.py for {symbol} (full timeseries)")

        command = [
            sys.executable,
            collect_data_script_path,
            "--symbol", symbol,
            "--api-key", api_key,
            "--output-dir", DATA_DIR
        ]

        process_error_message = None
        try:
            process = subprocess.run(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False
            )
            if process.returncode != 0:
                error_output = process.stderr.strip() if process.stderr else process.stdout.strip()
                process_error_message = f"collect_data.py script failed for {symbol}: {error_output} (Exit code: {process.returncode})"
            else:
                status_updates.append(f"collect_data.py script executed successfully for {symbol}.")
                if process.stdout:
                    status_updates.append(f"collect_data.py output: {process.stdout.strip()}")

        except Exception as e_sub:
            process_error_message = f"Failed to execute collect_data.py for {symbol}: {str(e_sub)}"

        if process_error_message:
            status_updates.append(process_error_message)
            print(process_error_message)
            # Return immediately if script execution failed
            return {"status": "failed", "message": process_error_message, "detailed_log": status_updates, "output_filepath": None}

        # --- Process the output from collect_data.py ---
        # Expected filename from collect_data.py (after its internal changes)
        full_timeseries_filename = f"{symbol}_M1_full_timeseries.csv"
        full_timeseries_filepath = os.path.join(DATA_DIR, full_timeseries_filename)

        if not os.path.exists(full_timeseries_filepath):
            no_full_data_msg = f"collect_data.py ran but the expected output file '{full_timeseries_filename}' was not found in {DATA_DIR}."
            status_updates.append(no_full_data_msg)
            print(no_full_data_msg)
            return {"status": "failed", "message": no_full_data_msg, "detailed_log": status_updates, "output_filepath": None}

        status_updates.append(f"Full timeseries data file '{full_timeseries_filename}' found. Proceeding with filtering.")

        try:
            df_full = pd.read_csv(full_timeseries_filepath)
            if 'Timestamp' not in df_full.columns:
                raise ValueError("Timestamp column missing in the full timeseries data.")
            df_full['Timestamp'] = pd.to_datetime(df_full['Timestamp'])

            # Construct start and end datetimes for filtering
            # Ensure start_datetime is the beginning of the start_month
            start_datetime = datetime(int(req_start_year), int(req_start_month), 1, 0, 0, 0)
            # Ensure end_datetime is the end of the end_month.
            # One way: get first day of next month, then subtract one microsecond, or handle by inclusive upper bound.
            # Using pd.Timestamp for robust end-of-month:
            end_of_month_dt = pd.Timestamp(datetime(int(req_end_year), int(req_end_month), 1)) + pd.offsets.MonthEnd(1)
            # Ensure time part covers the whole day for the end_datetime
            end_datetime = end_of_month_dt.replace(hour=23, minute=59, second=59, microsecond=999999)


            status_updates.append(f"Filtering data from {start_datetime.strftime('%Y-%m-%d %H:%M:%S')} to {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}.")

            df_filtered = df_full[(df_full['Timestamp'] >= start_datetime) & (df_full['Timestamp'] <= end_datetime)]

            if df_filtered.empty:
                no_data_in_range_msg = f"Successfully fetched full timeseries for {symbol}, but no data found for the specified range: {req_start_year}-{req_start_month} to {req_end_year}-{req_end_month}."
                status_updates.append(no_data_in_range_msg)
                # This is not necessarily a "failed" status for the whole job, but no output file for this range.
                # Depending on desired behavior, could be "completed" with this message. For now, let's treat as no output.
                final_status = "completed" # Or "failed" if no data in range is a hard failure
                final_message = no_data_in_range_msg
                output_filepath = None # No specific file for this range
            else:
                # Save the filtered DataFrame
                s_year_str = str(req_start_year)
                s_month_str = str(req_start_month).zfill(2)
                e_year_str = str(req_end_year)
                e_month_str = str(req_end_month).zfill(2)

                filtered_filename = f"{symbol}_{s_year_str}{s_month_str}_{e_year_str}{e_month_str}.csv"
                output_filepath = os.path.join(DATA_DIR, filtered_filename)

                df_filtered.to_csv(output_filepath, index=False)
                status_updates.append(f"Filtered data saved to {output_filepath} ({len(df_filtered)} rows).")
                print(f"Filtered data saved to {output_filepath}")
                final_status = "completed"
                final_message = f"Data collection and filtering successful. Output file: {output_filepath}"

        except Exception as e_filter:
            filter_error_msg = f"Error during data processing/filtering for {symbol}: {str(e_filter)}"
            status_updates.append(filter_error_msg)
            print(filter_error_msg)
            final_status = "failed"
            final_message = filter_error_msg
            output_filepath = None

    except Exception as e: # Catch-all for unexpected errors during setup
        error_msg = f"An unexpected error occurred during data collection setup: {str(e)}"
        print(f"Outer exception in _blocking_data_collection_simulation: {error_msg}")
        status_updates.append(error_msg)
        final_status = "failed" # Ensure status is failed
        final_message = error_msg
        output_filepath = None

    return {"status": final_status, "message": final_message, "detailed_log": status_updates, "output_filepath": output_filepath}


def manage_blocking_data_collection(job_id: str, request_params: dict):
    """
    Manages the data collection by running _blocking_data_collection_simulation in a thread.
    Updates the job_store with the results.
    """
    try:
        # Update job status to running before starting the thread
        job_store[job_id]["status"] = "running"
        job_store[job_id]["message"] = "Data collection process has started."

        # Define a target function for the thread that calls the simulation
        # and updates the job store with its results.
        def thread_target():
            collection_result = _blocking_data_collection_simulation(request_params)
            job_store[job_id].update({
                "status": collection_result.get("status", "failed"),
                "message": collection_result.get("message", "An unknown error occurred in the collection worker."),
                "detailed_log": collection_result.get("detailed_log", []),
                "output_filepath": collection_result.get("output_filepath")
            })
            if collection_result.get("status") == "completed":
                 print(f"Job {job_id} completed successfully: {collection_result.get('message')}")
            else:
                 print(f"Job {job_id} failed or completed with errors: {collection_result.get('message')}")


        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()

    except Exception as e:
        # This handles errors in setting up the thread, not errors inside the thread.
        job_store[job_id].update({
            "status": "failed",
            "message": f"Failed to start data collection thread: {str(e)}"
        })
        print(f"Error starting data collection thread for job {job_id}: {str(e)}")


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
    background_tasks.add_task(manage_blocking_data_collection, job_id, request.model_dump())
    return JobCreationResponse(job_id=job_id)


@app.get("/api/data/status/{job_id}", response_model=JobStatusResponse)
async def get_data_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job or job.get("type") != "data_collection":
        raise HTTPException(status_code=404, detail="Data collection job not found or job ID is not for a data collection task.")

    status = job["status"]
    message = job.get("message") # Get message set by the background task or initiator

    # Provide more specific default messages if not set by the task
    if not message:
        if status == "completed":
            message = "Data collection job completed successfully."
        elif status == "pending":
            message = "Data collection job is pending."
        elif status == "running":
            message = "Data collection job is currently running."
        elif status == "failed":
            message = "Data collection job failed." # Specific failure message should be in job.get("message")
        else:
            message = "Data collection job status unknown."

    return JobStatusResponse(job_id=job_id, status=status, message=message)


@app.get("/api/backtest/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job["status"]
    # Prioritize specific message from job_store, fallback to generic status messages
    message = job.get("message") # Get message set by the background task first

    if status == "failed":
        # If a specific error_message exists, it's usually more detailed for failures
        message = job.get("error_message", message if message else "An unknown error occurred.")
    elif not message: # If no specific message was set in job_store by the task
        if status == "completed":
            message = "Job completed successfully."
        elif status == "pending":
            message = "Job is pending." # Default pending message if not set by initiator
        elif status == "running":
            message = "Job is currently running."
        else:
            message = "Job status unknown." # Fallback for any other status

    # Ensure 'pending' jobs that had an initial message retain it if not overwritten by a more specific one above
    if status == "pending" and job.get("message") and not message:
        message = job.get("message")


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
                await asyncio.sleep(0.05)  # Wait 0.05 seconds
            elif status == "completed":
                await websocket.send_text(f"INFO: Job {job_id} completed. {current_job_info.get('message', '')}")
                break
            elif status == "failed":
                await websocket.send_text(f"ERROR: Job {job_id} failed. {current_job_info.get('message', '')}")
                break
            elif status == "pending":
                 await websocket.send_text(f"INFO: Job {job_id} is pending. Waiting for it to start...")
                 await asyncio.sleep(0.05) # Wait for job to start
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
