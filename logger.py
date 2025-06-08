import logging
import sys

def setup_logging(log_path, log_level_str):
    """Sets up the logging configuration."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set overall level to DEBUG, handlers control their own levels

    # Validate log_level_str
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # File Handler
    try:
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # If file handler fails, log to stderr and continue with console logging if possible
        sys.stderr.write(f"Failed to set up file handler for logging at {log_path}: {e}\n")


    # Stream Handler (Console)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level) # Use the same level as file handler, or make it configurable
    stream_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s') # Can be simpler for console
    stream_handler.setFormatter(stream_formatter)
    root_logger.addHandler(stream_handler)

    # Initial log to confirm setup (optional)
    # root_logger.info(f"Logging initialized. Log level: {log_level_str}. Log file: {log_path}")

def get_logger(name):
    """Gets a logger instance with the given name."""
    return logging.getLogger(name)
