import sys
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the root directory to sys.path to allow imports from trading_logic, etc.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import trading_logic
import performance_analyzer
import data_loader
# config_loader might not be directly used if API passes all config

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
    realized_pnl: Any
    type: Any # Could be 'entry', 'exit', 'stop_loss', etc.

class BacktestResultsResponse(BaseModel):
    job_id: str
    status: str
    results: Optional[Dict[str, Any]] = None # For KPIs
    equity_curve: Optional[List[EquityDataPoint]] = None
    trade_log: Optional[List[TradeLogEntry]] = None
    message: Optional[str] = None

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
        raw_data_df = data_loader.load_csv_data('../historical_data.csv')

        if raw_data_df.empty:
            raise ValueError("Loaded data is empty.")
        if 'Timestamp' not in raw_data_df.columns:
            # Assuming data_loader standardizes this, but good to check or ensure
            # Or if data_loader is expected to return a dict of DFs, adapt this
            raise ValueError("Timestamp column missing in loaded data.")

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
            historical_data=historical_data_dict,
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
            risk_free_rate=risk_free_rate
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
        "parameters": settings.dict(),
        "kpis": None,
        "equity_curve": None,
        "trade_log": None,
        "error_message": None,
        "message": "Job initiated." # Optional: a more descriptive initial message
    }
    background_tasks.add_task(run_backtest_task, job_id, settings.dict())
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
