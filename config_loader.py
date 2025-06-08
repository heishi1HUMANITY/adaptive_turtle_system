import json

def load_config(config_path):
  """Loads trading parameters from a JSON configuration file.

  Args:
    config_path: Path to the JSON configuration file.

  Returns:
    A dictionary containing the loaded trading parameters.
  """
  with open(config_path, 'r') as f:
    config = json.load(f)
  return config
