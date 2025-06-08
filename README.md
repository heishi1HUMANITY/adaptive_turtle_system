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
