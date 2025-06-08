# Trading System Project

This project is the foundation for a trading system, including configuration management and data handling capabilities.

## Project Structure

```
.
├── config.json         # Trading parameters
├── config_loader.py    # Script to load configuration
├── data_loader.py      # Script to load historical data
├── historical_data.csv # Sample historical data
└── requirements.txt    # Python dependencies
```

## Setup

1.  **Clone the repository (if applicable)**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Create and activate a virtual environment (recommended)**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Configuration Management

The `config.json` file stores trading parameters. You can load these parameters into your Python scripts using the `config_loader.py` module.

**Example:**

```python
from config_loader import load_config

config = load_config('config.json')
print(f"Market: {config.get('market')}")
print(f"Timeframe: {config.get('timeframe')}")
```

### Additional Configuration Options

Beyond the basic trading parameters, `config.json` can also include settings for system behavior:

**Logging Configuration:**

The `logging` object configures the system's logging behavior.

*   `log_file_path` (string): Specifies the path to the log file where trading activities and system messages will be recorded.
    *   Example: `"log_file_path": "trading_system.log"`
*   `log_level` (string): Defines the minimum severity level of messages to be logged. Common values include:
    *   `"DEBUG"`: Detailed information, typically of interest only when diagnosing problems.
    *   `"INFO"`: Confirmation that things are working as expected.
    *   `"WARNING"`: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., ‘disk space low’). The software is still working as expected.
    *   `"ERROR"`: Due to a more serious problem, the software has not been able to perform some function.
    *   `"CRITICAL"`: A serious error, indicating that the program itself may be unable to continue running.
    *   Default: If not specified, the system might default to "INFO".
    *   Example: `"log_level": "INFO"`

**Example `logging` object:**
```json
{
  "logging": {
    "log_file_path": "trading_system.log",
    "log_level": "INFO"
  }
}
```

**Emergency Stop:**

*   `emergency_stop` (boolean): A flag to control new trade entries.
    *   Purpose: When set to `true`, the system will not open any new positions. Existing positions will continue to be managed (i.e., stop-loss and take-profit orders will still be processed). This allows for a controlled halt of new trading activity without immediately liquidating the portfolio.
    *   Values:
        *   `true`: Activates the emergency stop, preventing new trades.
        *   `false`: Deactivates the emergency stop, allowing new trades as per strategy logic.
    *   Default: If the key is missing from `config.json`, the system defaults to `false` (normal operation).
    *   Example: `"emergency_stop": false`

### Data Acquisition

The `data_loader.py` module can read historical data from CSV files into a Pandas DataFrame. The `Timestamp` column is automatically parsed as datetime objects.

**Example:**

```python
from data_loader import load_csv_data

try:
    data_df = load_csv_data('historical_data.csv')
    print("Data loaded successfully:")
    print(data_df.head())
    print("\nData types:")
    print(data_df.dtypes)
except FileNotFoundError:
    print("Error: historical_data.csv not found.")
except Exception as e:
    print(f"An error occurred: {e}")

```

### Trading Logic Core

The `trading_logic.py` file contains the core financial calculations and logic for the trading system. This module provides functionalities for calculating technical indicators, generating trading signals, and determining position sizes.

**Key Functionalities:**

*   **Technical Indicators**:
    *   `calculate_donchian_channel(high, low, period)`: Calculates Donchian Channel upper and lower bands.
    *   `calculate_atr(high, low, close, period)`: Calculates Average True Range.
*   **Signal Generation**:
    *   `generate_entry_signals(close, donchian_upper, donchian_lower, entry_period)`: Generates entry signals based on Donchian breakouts.
    *   `generate_exit_signals(close, donchian_upper_exit, donchian_lower_exit, exit_period_long, exit_period_short, current_positions)`: Generates exit signals.
*   **Position Sizing**:
    *   `calculate_position_size(...)`: Calculates position size based on account equity, risk parameters, ATR, and other constraints. (See function signature for full arguments).

**Example: Calculating Donchian Channels**

```python
import pandas as pd
import trading_logic as tl # Assuming trading_logic.py is accessible

# Sample data (replace with your actual data)
data = {
    'high': [10, 12, 11, 13, 14, 15],
    'low':  [8,  9,  10, 10, 11, 12],
    'close':[9,  11, 10, 12, 13, 14]
}
df = pd.DataFrame(data)

period = 3 # Define Donchian period
upper_band, lower_band = tl.calculate_donchian_channel(df['high'], df['low'], period)

print("Donchian Upper Band:")
print(upper_band)
print("\\nDonchian Lower Band:")
print(lower_band)
```
