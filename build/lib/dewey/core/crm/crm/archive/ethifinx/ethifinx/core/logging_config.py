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


def setup_logging(
    name: str,
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Set up logging configuration for the given module.

    Args:
        name: Name of the logger (typically __name__)
        level: Optional logging level (defaults to LOG_LEVEL)
        log_file: Optional log file path (defaults to LOG_FILE)
        log_format: Optional log format string (defaults to LOG_FORMAT)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Use default values if not provided
    level = level or LOG_LEVEL
    log_file = log_file or LOG_FILE
    log_format = log_format or LOG_FORMAT

    logger.setLevel(level)

    # Create formatters and handlers
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent duplicate logging
    logger.propagate = False

    return logger
