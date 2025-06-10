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
    successful_csv_files = []
    first_error_message = None
    # Default to failure until success is explicitly determined
    final_status = "failed"
    final_message = "Data collection process did not start or encountered an unexpected issue."

    try:
        symbol = request_params.get("symbol")
        start_year = request_params.get("startYear")
        start_month = request_params.get("startMonth")
        end_year = request_params.get("endYear")
        end_month = request_params.get("endMonth")
        api_key = request_params.get("apiKey")

        if not api_key:
            return {"status": "failed", "message": "API key is missing."}

        if not all([symbol, start_year, start_month, end_year, end_month]):
            return {"status": "failed", "message": "Missing required parameters for data collection."}

        current_year = int(start_year)
        current_month = int(start_month)
        target_end_year = int(end_year)
        target_end_month = int(end_month)

        script_dir = os.path.dirname(__file__)
        project_root = os.path.join(script_dir, '..')
        collect_data_script_path = os.path.join(project_root, 'collect_data.py')

        # Ensure DATA_DIR exists (though collect_data.py might also do this)
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

        while (current_year < target_end_year) or \
              (current_year == target_end_year and current_month <= target_end_month):

            month_str = str(current_month).zfill(2)
            year_str = str(current_year)

            status_updates.append(f"Collecting data for {symbol} {year_str}-{month_str}...")
            print(f"Running collect_data.py for {symbol} {year_str}-{month_str}") # Server log

            command = [
                sys.executable,
                collect_data_script_path,
                "--symbol", symbol,
                "--year", year_str,
                "--month", month_str,
                "--api-key", api_key,
                "--output-dir", DATA_DIR
            ]

            try:
                process = subprocess.run(
                    command,
                    cwd=project_root, # Run from project root
                    capture_output=True,
                    text=True,
                    check=False # Do not raise exception on non-zero exit, handle manually
                )

                if process.returncode != 0:
                    error_output = process.stderr.strip() if process.stderr else process.stdout.strip()
                    error_msg = f"Error collecting data for {year_str}-{month_str}: {error_output} (Exit code: {process.returncode})"
                    status_updates.append(error_msg)
                    print(error_msg) # Server log
                    if not first_error_message: # Store first error
                        first_error_message = error_msg
                    # As per instruction: "collect as much as possible and report errors"
                    # So, we continue to the next month. If we wanted to stop, we'd set final_status = "failed" here.
                else:
                    success_msg = f"Successfully collected data for {year_str}-{month_str}."
                    if process.stdout:
                        success_msg += f" Output: {process.stdout.strip()}"
                    status_updates.append(success_msg)
                    print(success_msg) # Server log
                    # Assume collect_data.py generates a file named SYMBOL_YEAR_MONTH.csv
                    # This needs to match actual output of collect_data.py
                    individual_csv_name = f"{symbol}_{year_str}_{month_str}.csv"
                    individual_csv_path = os.path.join(DATA_DIR, individual_csv_name)
                    if os.path.exists(individual_csv_path): # Check if file was actually created
                        successful_csv_files.append(individual_csv_path)
                        status_updates.append(f"Added {individual_csv_path} to merge list.")
                    else:
                        error_msg_file_missing = f"Data for {year_str}-{month_str} collected by script, but output file {individual_csv_path} not found."
                        status_updates.append(error_msg_file_missing)
                        print(error_msg_file_missing) # Server log
                        if not first_error_message:
                            first_error_message = error_msg_file_missing
                        # Consider this a partial failure for the month.

            except Exception as e_sub: # Catch errors from subprocess.run itself
                error_msg = f"Subprocess execution failed for {year_str}-{month_str}: {str(e_sub)}"
                status_updates.append(error_msg)
                print(error_msg) # Server log
                if not first_error_message:
                    first_error_message = error_msg
                # Continue to next month

            # Increment month and year
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        # CSV Merging Logic
        if successful_csv_files:
            status_updates.append(f"Attempting to merge {len(successful_csv_files)} successfully downloaded CSV file(s).")
            print(f"Attempting to merge {len(successful_csv_files)} CSV file(s).")
            all_dataframes = []
            for f_path in successful_csv_files:
                try:
                    df = pd.read_csv(f_path)
                    if not df.empty:
                        all_dataframes.append(df)
                        status_updates.append(f"Read {f_path} for merging.")
                    else:
                        status_updates.append(f"Warning: {f_path} is empty, skipping.")
                        print(f"Warning: {f_path} is empty, skipping.")
                except Exception as e_read:
                    read_err_msg = f"Error reading CSV file {f_path} for merging: {str(e_read)}"
                    status_updates.append(read_err_msg)
                    print(read_err_msg)
                    if not first_error_message: # Capture as a processing error
                        first_error_message = read_err_msg

            if all_dataframes:
                try:
                    combined_df = pd.concat(all_dataframes, ignore_index=True)

                    # Ensure 'Timestamp' column exists and sort
                    if 'Timestamp' in combined_df.columns:
                        combined_df['Timestamp'] = pd.to_datetime(combined_df['Timestamp'])
                        combined_df.sort_values(by='Timestamp', inplace=True)
                        status_updates.append("Combined DataFrame sorted by Timestamp.")
                    else:
                        status_updates.append("Warning: 'Timestamp' column not found in combined data. Cannot sort by time.")
                        print("Warning: 'Timestamp' column not found in combined data.")

                    # Construct combined filename
                    s_year_str = str(request_params.get("startYear"))
                    s_month_str = str(request_params.get("startMonth")).zfill(2)
                    e_year_str = str(request_params.get("endYear"))
                    e_month_str = str(request_params.get("endMonth")).zfill(2)
                    combined_filename = f"{symbol}_{s_year_str}{s_month_str}_{e_year_str}{e_month_str}.csv"
                    output_filepath = os.path.join(DATA_DIR, combined_filename)

                    combined_df.to_csv(output_filepath, index=False)
                    status_updates.append(f"Successfully merged data to {output_filepath}.")
                    print(f"Successfully merged data to {output_filepath}.")

                    if not first_error_message: # All subprocess calls and merge succeeded
                        final_status = "completed"
                        final_message = f"Data collection and merging successful. Combined file: {output_filepath}"
                    else: # Subprocess calls had errors, but merge was successful with partial data
                        final_status = "completed" # Still "completed" for partial success if merge happens
                        final_message = f"Data collection partially successful. Some months had errors. Combined file: {output_filepath}"

                except Exception as e_merge:
                    merge_err_msg = f"Error during CSV merging process: {str(e_merge)}"
                    status_updates.append(merge_err_msg)
                    print(merge_err_msg)
                    if not first_error_message:
                        first_error_message = merge_err_msg
                    final_status = "failed"
                    final_message = f"Data collection failed during CSV merging: {first_error_message}"
                    output_filepath = None # Ensure no filepath on merge failure

            elif not first_error_message: # Files were listed but all were empty/unreadable
                final_status = "failed"
                final_message = "Data collection failed: Successfully fetched month files were empty or unreadable."
                status_updates.append("No dataframes could be read from successfully fetched files. Merge aborted.")
                output_filepath = None
            else: # Files were listed, all empty/unreadable, AND there was a previous subprocess error
                final_status = "failed"
                final_message = f"Data collection failed: {first_error_message}. Additionally, successfully fetched month files were empty or unreadable."
                status_updates.append("No dataframes could be read from successfully fetched files. Merge aborted.")
                output_filepath = None

        elif not first_error_message: # No CSVs created and no prior errors from subprocess.
            final_status = "failed"
            final_message = "Data collection failed: No data files were created for the specified period."
            status_updates.append("No individual CSV files were successfully created. Nothing to merge.")

        else: # No CSVs created AND there were subprocess errors
            final_status = "failed"
            final_message = f"Data collection failed: {first_error_message}. No data files were created."
            status_updates.append("No individual CSV files were successfully created due to errors. Nothing to merge.")

    except Exception as e:
        error_msg = f"An unexpected error occurred during data collection: {str(e)}"
        print(f"Outer exception in _blocking_data_collection_simulation: {error_msg}") # Server log
        status_updates.append(error_msg)
        # Ensure these are set if an outer exception occurs
        final_status = "failed"
        final_message = error_msg
        output_filepath = None # No output file if there's a major error

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
