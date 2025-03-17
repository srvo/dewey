import logging
from pathlib import Path
from typing import Optional

from ethifinx.core.logging_config import LOG_FILE, LOG_FORMAT, LOG_LEVEL


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    format_str: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with the specified name and configuration.

    Args:
        name (str): Name of the logger.
        log_file (Path, optional): Path for log file. Defaults to LOG_FILE.
        level (int, optional): Logging level. Defaults to LOG_LEVEL.
        format_str (str, optional): Log format string. Defaults to LOG_FORMAT.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(level or LOG_LEVEL)

    # Use config defaults if not specified
    log_file = log_file or LOG_FILE
    format_str = format_str or LOG_FORMAT
    formatter = logging.Formatter(format_str)

    # File handler
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one with default configuration.

    Args:
        name (str): Name of the logger.

    Returns:
        logging.Logger: Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
