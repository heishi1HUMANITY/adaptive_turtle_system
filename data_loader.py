import pandas as pd
from logger import get_logger
import os # Added import

data_logger = get_logger(__name__)

def load_csv_data(file_path):
  """Loads historical market data from a CSV file.

  Args:
    file_path: Path to the CSV file. If relative, it's resolved
               relative to this data_loader.py file's location.

  Returns:
    A Pandas DataFrame containing the loaded data, with the 'Timestamp'
    column parsed as datetime objects. Returns an empty DataFrame on error.
  """

  # Construct absolute path if file_path is relative
  if not os.path.isabs(file_path):
    # __file__ is the path to the current script (data_loader.py)
    # os.path.dirname(__file__) is the directory where data_loader.py resides
    # os.path.join combines it with the relative file_path
    # os.path.abspath ensures it's an absolute path
    script_dir = os.path.dirname(__file__)
    # If script_dir is empty (e.g. when run in an interactive session not from a file),
    # default to current working directory for relative paths.
    if not script_dir:
        script_dir = '.'
    absolute_file_path = os.path.abspath(os.path.join(script_dir, file_path))
  else:
    absolute_file_path = file_path

  data_logger.info(f"Attempting to load data from resolved path: {absolute_file_path}")

  try:
    df = pd.read_csv(absolute_file_path, parse_dates=['Timestamp'])
    df = df.set_index('Timestamp')
    data_logger.info(f"Successfully loaded data from {absolute_file_path}.")
    return df
  except FileNotFoundError:
    data_logger.error(f"Data file not found: {absolute_file_path}")
    raise # Re-raise the exception after logging
  except pd.errors.EmptyDataError:
    data_logger.error(f"Data file is empty: {absolute_file_path}")
    raise # Re-raise
  except Exception as e:
    data_logger.exception(f"An unexpected error occurred while loading data from {absolute_file_path}")
    raise # Re-raise
