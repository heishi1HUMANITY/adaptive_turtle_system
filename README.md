# Trading System Project

## Project Overview

This project implements a trading system with data collection, backtesting capabilities, and a foundational structure for a web-based frontend and a Python backend.

- **Frontend**: Provides the user interface for interacting with the system. Currently, this is a standard React setup. More details can be found in `frontend/README.md`.
- **Backend**: Handles business logic, data processing, and API services. This is a FastAPI application. More details can be found in `backend/README.md`.

This project also includes several key Python scripts:
- `collect_data.py`: Responsible for fetching historical forex data from an external API (Alpha Vantage) and saving it.
- `main_backtest.py`: Used to run the trading strategy backtest using historical data, configuration, and trading logic.
- `trading_logic.py`: Contains the core financial calculations, technical indicator computations, signal generation, and position sizing logic.
- `config_loader.py`: Handles loading of trading parameters and system settings from `config.json`.
- `data_loader.py`: Manages loading of historical price data from CSV files for backtesting or analysis.
- `performance_analyzer.py`: Calculates various performance metrics (KPIs) for the backtest results and generates reports.
- `logger.py`: Configures and provides logging functionality for the system.

## Project Structure

```
.
├── backend/              # FastAPI backend application
│   ├── main.py
│   ├── requirements.txt
│   ├── start_backend.sh
│   ├── start_backend.ps1 # PowerShell script for backend
│   └── README.md
├── frontend/             # React frontend application
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── start_frontend.sh
│   ├── start_frontend.ps1 # PowerShell script for frontend
│   └── README.md
├── start_all.sh        # Script to start both backend and frontend (Linux/macOS)
├── start_all.ps1       # Script to start both backend and frontend (Windows PowerShell)
├── config.json         # Trading parameters and system settings
├── config_loader.py    # Script to load configuration
├── data_loader.py      # Script to load historical data
├── historical_data.csv # Sample historical data
├── collect_data.py     # Script to fetch historical data
├── main_backtest.py    # Main script to run backtests
├── trading_logic.py    # Core trading strategy logic
├── performance_analyzer.py # Script to analyze backtest performance
├── logger.py           # Logging utility
└── requirements.txt    # Python dependencies for core scripts
```

## Setup

1.  **Clone the repository (if applicable)**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Environment Setup**:
    *   **For Core Python Scripts**: Create and activate a virtual environment.
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
        Install dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   **For Backend**: Navigate to the `backend` directory and follow instructions in `backend/README.md`.
    *   **For Frontend**: Navigate to the `frontend` directory and follow instructions in `frontend/README.md`.

## Dependency Management
This project uses Dependabot to automatically keep dependencies up to date. Dependabot will create pull requests to update npm and pip packages as new versions become available.

## Quick Start: Running the Full Application

To quickly start both the backend and frontend applications for development, use the `start_all.sh` script located in the project root:

```bash
./start_all.sh
```
*(Ensure the script is executable: `chmod +x start_all.sh`)*

This script will:
1.  Start the backend server in the background. The PID (Process ID) of the backend server will be displayed.
2.  Wait for a few seconds to allow the backend to initialize.
3.  Start the frontend development server in the foreground.

**Stopping the Services:**
*   **Frontend**: Press `Ctrl+C` in the terminal where `start_all.sh` is running (as it's the foreground process).
*   **Backend**: The script will output a command like `kill $BACKEND_PID` (where `$BACKEND_PID` is the actual Process ID). Run this command in a new terminal to stop the backend server. Alternatively, you can find the backend process listening on port 8000 (or the configured port) and kill it manually.

**Note**: These `start_all.sh` and `start_all.ps1` scripts (by calling the individual backend and frontend start scripts) will also ensure that all necessary backend (`pip install -r requirements.txt`) and frontend (`npm install`) dependencies are installed or updated before launching the services.

### Running on Windows (PowerShell)
For Windows users, a PowerShell script is available to start both services:
```powershell
.\start_all.ps1
```
This will open separate PowerShell windows for the backend and frontend. To stop the services, simply close these windows. Ensure your execution policy allows running local scripts (e.g., by running `Set-ExecutionPolicy RemoteSigned -Scope Process` in PowerShell). As mentioned above, this script also handles dependency installation.

## Detailed Usage

### 1. Data Collection

Use `collect_data.py` to fetch historical market data.
```bash
python collect_data.py --symbol YOUR_SYMBOL --api-key YOUR_API_KEY --output-dir ./
```
This will save data to a CSV file (e.g., `YOUR_SYMBOL_M1_full_timeseries.csv`). Rename this to `historical_data.csv` or update `config.json` if you wish to use it for backtesting.

### 2. Configuration Management

The `config.json` file stores trading parameters and system settings. `config_loader.py` is used by other scripts to load these settings.

Key sections in `config.json`:
*   Trading parameters (e.g., `market`, `timeframe`, strategy-specific parameters).
*   `logging`: Configures log file path and level.
*   `emergency_stop`: A boolean flag to halt new trade entries.
*   `initial_capital`: Starting capital for backtests.
*   `risk_free_rate_annual`: Annual risk-free rate for KPI calculations.
*   `markets`: List of markets to trade (currently, `main_backtest.py` loads data for the first market from `historical_data.csv`).

**Example `config.json` snippet:**
```json
{
  "market": "EURUSD",
  "timeframe": "H1",
  "donchian_period_entry": 20,
  "donchian_period_exit_long": 10,
  "donchian_period_exit_short": 10,
  "atr_period": 14,
  "risk_per_trade_percentage": 1.0,
  "initial_capital": 100000.0,
  "logging": {
    "log_file_path": "trading_system.log",
    "log_level": "INFO"
  },
  "emergency_stop": false,
  "markets": ["YOUR_SYMBOL_M1"],
  "risk_free_rate_annual": 0.02
}
```

### 3. Running a Backtest

Execute `main_backtest.py` to run a trading strategy simulation on historical data.
```bash
python main_backtest.py
```
This script will:
1.  Load settings from `config.json`.
2.  Load data from `historical_data.csv` (as specified by `data_loader.py`).
3.  Apply the logic from `trading_logic.py`.
4.  Calculate performance metrics using `performance_analyzer.py`.
5.  Generate a `backtest_report.txt` with the results.

### 4. Data Loading

`data_loader.py` is used internally by `main_backtest.py` to load historical data. It expects a CSV file with 'Timestamp', 'Open', 'High', 'Low', 'Close', and 'Volume' columns.

### 5. Trading Logic Core

`trading_logic.py` contains the actual strategy. It includes functions for:
*   Calculating technical indicators (e.g., Donchian Channels, ATR).
*   Generating entry and exit signals.
*   Calculating position sizes.

### 6. Frontend and Backend Applications

-   **Backend API**: Run the FastAPI server from the `backend` directory. See `backend/README.md` for details.
-   **Frontend Application**: Run the React development server from the `frontend` directory. See `frontend/README.md` for details.

Ensure the backend is running before starting the frontend if the frontend needs to make API calls on startup.
The frontend includes a health check to `/api/health` on the backend.
