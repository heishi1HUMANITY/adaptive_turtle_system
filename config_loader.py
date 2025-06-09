import json
from logger import get_logger

config_logger = get_logger(__name__)

def load_config(config_path):
  """Loads trading parameters from a JSON configuration file.

  Args:
    config_path: Path to the JSON configuration file.

  Returns:
    A dictionary containing the loaded trading parameters, or None if loading fails.
  """
  try:
    with open(config_path, 'r') as f:
      config = json.load(f)
    config_logger.info(f"Configuration loaded successfully from {config_path}.")
    return config
  except FileNotFoundError:
    config_logger.error(f"Configuration file not found: {config_path}")
    raise  # Or return None, depending on desired error handling
  except json.JSONDecodeError as e:
    config_logger.error(f"Error decoding JSON from configuration file: {config_path} - {e}")
    raise  # Or return None
  except Exception as e:
    config_logger.exception(f"An unexpected error occurred while loading configuration from {config_path}")
    raise  # Or return None
