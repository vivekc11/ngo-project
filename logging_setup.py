# logging_setup.py / not in use yet
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name: str, log_file: str = "app.log", level=logging.INFO) -> logging.Logger:
    """Creates and returns a logger with a rotating file handler and console output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        return logger  # Prevent duplicate handlers if already set

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotating file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
