import logging
from pathlib import Path
from typing import Optional

from ethifinx.core.logging_config import LOG_FILE, LOG_FORMAT, LOG_LEVEL


def _configure_logger(
    logger: logging.Logger,
    log_file: Path,
    level: int,
    format_str: str,
) -> None:
    """Configures a logger with the specified settings.

    Args:
        logger: The logger instance to configure.
        log_file: The path to the log file.
        level: The logging level.
        format_str: The log format string.

    """
    formatter = logging.Formatter(format_str)

    # File handler
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def setup_logger(
    name: str,
    log_file: Path | None = None,
    level: int | None = None,
    format_str: str | None = None,
) -> logging.Logger:
    """Sets up a logger with the specified name and configuration.

    Args:
        name: Name of the logger.
        log_file: Path for log file. Defaults to LOG_FILE.
        level: Logging level. Defaults to LOG_LEVEL.
        format_str: Log format string. Defaults to LOG_FORMAT.

    Returns:
        Configured logger instance.

    """
    logger = logging.getLogger(name)

    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    log_level = level if level is not None else LOG_LEVEL
    logger.setLevel(log_level)

    # Use config defaults if not specified
    log_file = log_file if log_file is not None else LOG_FILE
    format_str = format_str if format_str is not None else LOG_FORMAT

    _configure_logger(logger, log_file, log_level, format_str)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Gets an existing logger or creates a new one with default configuration.

    Args:
        name: Name of the logger.

    Returns:
        Logger instance.

    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
