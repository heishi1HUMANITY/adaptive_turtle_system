import pandas as pd
from logger import get_logger

data_logger = get_logger(__name__)

def load_csv_data(file_path):
  """Loads historical market data from a CSV file.

  Args:
    file_path: Path to the CSV file.

  Returns:
    A Pandas DataFrame containing the loaded data, with the 'Timestamp'
    column parsed as datetime objects. Returns an empty DataFrame on error.
  """
  try:
    df = pd.read_csv(file_path, parse_dates=['Timestamp'])
    data_logger.info(f"Successfully loaded data from {file_path}.")
    return df
  except FileNotFoundError:
    data_logger.error(f"Data file not found: {file_path}")
    raise
  except pd.errors.EmptyDataError:
    data_logger.error(f"Data file is empty: {file_path}")
    raise
  except Exception as e:
    data_logger.exception(f"An unexpected error occurred while loading data from {file_path}")
    raise
