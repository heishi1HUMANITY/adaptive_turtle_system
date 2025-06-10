import sys
import os
import uuid
import asyncio # Ensure asyncio is imported
import pandas as pd # Added import
from datetime import datetime
from typing import List, Dict, Optional, Any
# Removed: from asyncio import Queue
# Removed: from fastapi import Depends

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import trading_logic
import performance_analyzer
import data_loader

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
    order_id: Any
    symbol: Any
    action: Any
    quantity: Any
    price: Any
    timestamp: Any
    commission: Any
    slippage: Any
    realized_pnl: Optional[float] = None
    type: Any

class BacktestResultsResponse(BaseModel):
    job_id: str
    status: str
    results: Optional[Dict[str, Any]] = None
    equity_curve: Optional[List[EquityDataPoint]] = None
    trade_log: Optional[List[TradeLogEntry]] = None
    message: Optional[str] = None

class DataCollectionRequest(BaseModel):
    symbol: str
    startYear: int
    startMonth: int
    endYear: int
    endMonth: int
    apiKey: Optional[str] = None

class FileInfo(BaseModel):
    name: str
    size: int
    created_at: datetime

class FileListResponse(BaseModel):
    files: List[FileInfo]
    total_files: int

# Job Store
job_store: Dict[str, Dict[str, Any]] = {}

# Removed _TEST_LOG_END_SENTINEL_
# Removed get_log_queue dependency function

async def run_backtest_task(job_id: str, settings_dict: dict):
    try:
        job_store[job_id]["status"] = "running"
        config_dict_for_run = settings_dict.copy()
        raw_data_df = data_loader.load_csv_data('historical_data.csv')
        if raw_data_df.empty:
            raise ValueError("Loaded data is empty.")
        if not isinstance(raw_data_df.index, pd.DatetimeIndex):
            raise ValueError("Data does not have a DatetimeIndex. 'Timestamp' column might be missing or not set as index.")
        required_columns = ['Open', 'High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in raw_data_df.columns]
        if missing_columns:
            raise ValueError(f"Missing essential data columns: {', '.join(missing_columns)}")
        historical_data_dict = {}
        if not config_dict_for_run.get("markets"):
            raise ValueError("Markets list is empty in settings.")
        first_market = config_dict_for_run["markets"][0]
        historical_data_dict[first_market] = raw_data_df
        backtest_engine_results = trading_logic.run_strategy(
            historical_data_dict=historical_data_dict,
            initial_capital=config_dict_for_run["initial_capital"],
            config=config_dict_for_run,
            emergency_stop_activated=False
        )
        risk_free_rate = config_dict_for_run.get('risk_free_rate', 0.0)
        kpi_results_dict = performance_analyzer.calculate_all_kpis(
            backtest_results=backtest_engine_results,
            config=config_dict_for_run,
            risk_free_rate_annual=risk_free_rate
        )
        job_store[job_id].update({
            "status": "completed",
            "kpis": kpi_results_dict,
            "equity_curve": backtest_engine_results.get("equity_curve"),
            "trade_log": backtest_engine_results.get("trade_log"),
            "error_message": None
        })
    except Exception as e:
        job_store[job_id].update({
            "status": "failed",
            "error_message": str(e),
            "kpis": None, "equity_curve": None, "trade_log": None
        })

async def run_datacollection_task(job_id: str, request_params: dict):
    try:
        job_store[job_id]["status"] = "running"
        await asyncio.sleep(5)
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["message"] = "Data collection finished."
    except Exception as e:
        job_store[job_id].update({ "status": "failed", "message": str(e) })

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "status": "pending", "parameters": settings.model_dump(),
        "kpis": None, "equity_curve": None, "trade_log": None,
        "error_message": None, "message": "Job initiated."
    }
    background_tasks.add_task(run_backtest_task, job_id, settings.model_dump())
    return JobCreationResponse(job_id=job_id)

@app.post("/api/data/collect", response_model=JobCreationResponse, status_code=202)
async def start_data_collection(request: DataCollectionRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job_store[job_id] = {
        "status": "pending", "type": "data_collection",
        "parameters": request.model_dump(), "message": "Data collection job initiated."
    }
    background_tasks.add_task(run_datacollection_task, job_id, request.model_dump())
    return JobCreationResponse(job_id=job_id)

@app.get("/api/backtest/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job["status"]
    message = job.get("message")
    if status == "failed":
        message = job.get("error_message", message if message else "An unknown error occurred.")
    elif not message:
        if status == "completed": message = "Job completed successfully."
        elif status == "pending": message = "Job is pending."
        elif status == "running": message = "Job is currently running."
        else: message = "Job status unknown."
    if status == "pending" and job.get("message") and not message:
        message = job.get("message")
    return JobStatusResponse(job_id=job_id, status=status, message=message)

@app.get("/api/backtest/results/{job_id}", response_model=BacktestResultsResponse)
async def get_job_results(job_id: str):
    job = job_store.get(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    status = job["status"]
    if status == "completed":
        raw_equity_curve = job.get("equity_curve")
        converted_equity_curve = [EquityDataPoint(timestamp=item[0], equity=item[1]) for item in raw_equity_curve] if raw_equity_curve else None
        return BacktestResultsResponse(
            job_id=job_id, status="completed", results=job.get("kpis"),
            equity_curve=converted_equity_curve, trade_log=job.get("trade_log")
        )
    elif status in ["pending", "running"]:
        return BacktestResultsResponse(job_id=job_id, status=status, message=f"Backtest is {status}. Please try again later.")
    elif status == "failed":
        return BacktestResultsResponse(job_id=job_id, status="failed", message=job.get("error_message", "An unknown error occurred."))
    else:
        raise HTTPException(status_code=500, detail=f"Unknown job status: {status}")

@app.websocket("/api/data/stream_log/{job_id}")
async def stream_log(websocket: WebSocket, job_id: str): # Signature reverted
    await websocket.accept()

    job_info = job_store.get(job_id)
    if not job_info or job_info.get("type") != "data_collection":
        await websocket.send_text(f"ERROR: Job ID {job_id} not found or is not a data collection job.")
        await websocket.close(code=1008)
        return

    await websocket.send_text(f"Streaming logs for data collection job {job_id}...")

    try:
        # This is the normal operation logic (reverted version from subtask 21/report _123)
        for i in range(10):
            current_job_info = job_store.get(job_id)
            if not current_job_info:
                await websocket.send_text(f"ERROR: Job {job_id} disappeared unexpectedly.")
                break
            status = current_job_info["status"]
            if status == "running":
                await websocket.send_text(f"LOG: Line {i+1} for job {job_id} (Status: {status})")
                await asyncio.sleep(1)
            elif status == "completed":
                await websocket.send_text(f"INFO: Job {job_id} completed. {current_job_info.get('message', '')}")
                break
            elif status == "failed":
                await websocket.send_text(f"ERROR: Job {job_id} failed. {current_job_info.get('message', '')}")
                break
            elif status == "pending":
                await websocket.send_text(f"INFO: Job {job_id} is pending. Waiting for it to start...")
                await asyncio.sleep(1)
            else:
                await websocket.send_text(f"INFO: Job {job_id} status is {status}. Ending log stream.")
                break

        final_job_info_normal = job_store.get(job_id, {})
        final_status_normal = final_job_info_normal.get("status", "unknown")
        final_message_normal = final_job_info_normal.get("message", "")
        await websocket.send_text(f"INFO: Log streaming ended for job {job_id}. Final status: {final_status_normal}. Message: {final_message_normal}")

    except WebSocketDisconnect:
        print(f"Client disconnected from job {job_id} log stream.")
    except Exception as e:
        error_message = f"ERROR: An error occurred during log streaming: {str(e)}"
        print(f"Error in log streaming for job {job_id}: {e}")
        try:
            await websocket.send_text(error_message)
        except Exception:
            pass
    finally:
        print(f"Closing WebSocket connection for job {job_id}")

@app.get("/api/data/files", response_model=FileListResponse)
async def list_data_files():
    found_files = []
    if not os.path.exists(DATA_DIR) or not os.path.isdir(DATA_DIR):
        print(f"Data directory {DATA_DIR} not found or is not a directory.")
        return FileListResponse(files=[], total_files=0)
    try:
        for f_name in os.listdir(DATA_DIR):
            file_path = os.path.join(DATA_DIR, f_name)
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
                    print(f"Error processing file {file_path}: {e}")
        return FileListResponse(files=found_files, total_files=len(found_files))
    except OSError as e:
        print(f"Error listing files in directory {DATA_DIR}: {e}")
        raise HTTPException(status_code=500, detail=f"Server error accessing data files: {str(e)}")
