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
