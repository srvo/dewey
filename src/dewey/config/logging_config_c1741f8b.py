```python
"""Logging configuration module."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Base paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
LOG_DIR: Path = BASE_DIR / "logs"
DATA_DIR: Path = BASE_DIR / "data"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOG_FILE: Path = LOG_DIR / "app.log"
LOG_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def _create_formatter(log_format: str) -> logging.Formatter:
    """Creates a logging formatter.

    Args:
        log_format: The format string for the log message.

    Returns:
        A logging.Formatter instance.
    """
    return logging.Formatter(log_format)


def _create_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
    """Creates a console handler.

    Args:
        formatter: The logging formatter to use.

    Returns:
        A logging.StreamHandler instance.
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    return console_handler


def _create_file_handler(log_file: Path, formatter: logging.Formatter) -> RotatingFileHandler:
    """Creates a rotating file handler.

    Args:
        log_file: The path to the log file.
        formatter: The logging formatter to use.

    Returns:
        A RotatingFileHandler instance.
    """
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    return file_handler


def setup_logging(
    name: str,
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """Sets up logging configuration for the given module.

    Args:
        name: Name of the logger (typically __name__).
        level: Optional logging level (defaults to LOG_LEVEL).
        log_file: Optional log file path (defaults to LOG_FILE).
        log_format: Optional log format string (defaults to LOG_FORMAT).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Use default values if not provided
    level = level or LOG_LEVEL
    log_file = log_file or LOG_FILE
    log_format = log_format or LOG_FORMAT

    logger.setLevel(level)

    # Create formatters and handlers
    formatter = _create_formatter(log_format)

    # Console handler
    console_handler = _create_console_handler(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = _create_file_handler(log_file, formatter)
    logger.addHandler(file_handler)

    # Prevent duplicate logging
    logger.propagate = False

    return logger
```
