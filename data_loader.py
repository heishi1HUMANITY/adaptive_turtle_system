import pandas as pd

def load_csv_data(file_path):
  """Loads historical market data from a CSV file.

  Args:
    file_path: Path to the CSV file.

  Returns:
    A Pandas DataFrame containing the loaded data, with the 'Timestamp'
    column parsed as datetime objects.
  """
  df = pd.read_csv(file_path, parse_dates=['Timestamp'])
  return df
