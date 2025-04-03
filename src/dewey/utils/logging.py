import logging
import os
import sys
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

try:
    import colorlog
except ImportError:
    colorlog = None


def load_config() -> dict[str, Any]:
    """Load configuration from dewey.yaml."""
    config_path = (
        Path(os.getenv("DEWEY_DIR", os.path.expanduser("~/dewey")))
        / "config"
        / "dewey.yaml"
    )
    with open(config_path) as f:
        return yaml.safe_load(f)


def setup_logging(
    name: str, log_dir: str | None = None, config: dict[str, Any] | None = None
) -> logging.Logger:
    """Set up logging with configuration from dewey.yaml.

    Args:
        name: Name of the logger (typically __name__ or script name)
        log_dir: Optional override for log directory
        config: Optional override for config (for testing)

    Returns:
        Configured logger instance

    """
    if config is None:
        config = load_config()

    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO"))

    # Set up root logger first
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers from root logger
    root_logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(
        fmt=log_config.get(
            "format", "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        ),
        datefmt=log_config.get("datefmt", "%Y-%m-%d %H:%M:%S"),
    )

    # Add console handler to root logger
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set up script-specific logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Add file handler if log_dir is specified
    if log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(exist_ok=True)
        log_file = log_dir_path / f"{name}.log"
        file_handler = _create_rotating_handler(
            log_file,
            maxBytes=log_config.get("maxBytes", 10 * 1024 * 1024),  # 10MB
            backupCount=log_config.get("backupCount", 5),
            formatter=formatter,
        )
        logger.addHandler(file_handler)

        # Clean up old logs if configured
        retention_days = log_config.get("retention_days", 3)
        if retention_days > 0:
            _cleanup_old_logs(log_dir_path, retention_days, logger)

    # Add colored console output if configured and available
    if log_config.get("colored_console", False) and colorlog is not None:
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt=log_config.get("datefmt", "%Y-%m-%d %H:%M:%S"),
        )
        console_handler.setFormatter(console_formatter)

    return logger


def get_logger(name: str, log_dir: str | None = None) -> logging.Logger:
    """Get or create a logger with the given name.

    This is the main entry point for getting a logger in the Dewey project.

    Args:
        name: Name of the logger (typically __name__ or script name)
        log_dir: Optional override for log directory

    Returns:
        Configured logger instance

    """
    return setup_logging(name, log_dir)


def _create_rotating_handler(
    log_file: Path,
    maxBytes: int = 10 * 1024 * 1024,
    backupCount: int = 5,
    formatter: logging.Formatter = None,
) -> RotatingFileHandler:
    """Create a rotating file handler with specified parameters.

    Args:
        log_file: Path to the log file
        maxBytes: Maximum size of log file before rotating (default: 10MB)
        backupCount: Number of backup files to keep (default: 5)
        formatter: Formatter to use for log messages

    Returns:
        Configured RotatingFileHandler

    """
    handler = RotatingFileHandler(
        log_file,
        maxBytes=maxBytes,
        backupCount=backupCount,
        encoding="utf-8",
    )

    if formatter:
        handler.setFormatter(formatter)

    return handler


def _cleanup_old_logs(
    log_dir: Path, retention_days: int, logger: logging.Logger
) -> None:
    """Delete log files older than retention_days.

    Args:
        log_dir: Directory containing log files
        retention_days: Number of days to keep log files
        logger: Logger instance for reporting cleanup actions

    """
    now = datetime.now()
    cutoff = now - timedelta(days=retention_days)

    for log_file in log_dir.glob("**/*.log"):  # Recursive search
        if (
            log_file.is_file()
            and datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff
        ):
            try:
                log_file.unlink()
                logger.info(f"Removed old log file: {log_file}")
            except Exception as e:
                logger.error(f"Error removing {log_file}: {e}")


def configure_logging(config: dict) -> None:
    """Configure logging with colored console output and file rotation.

    This function provides a simpler interface for setting up logging without
    requiring a BaseScript instance.

    Args:
        config: A dictionary containing logging configuration options

    """
    logger = logging.getLogger()
    logger.setLevel(config.get("level", logging.INFO))

    formatter = logging.Formatter(
        config.get("format", "%(asctime)s - %(levelname)s - %(message)s")
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(config.get("console_level", logging.INFO))
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    log_dir = Path(config.get("root_dir", "logs"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / config.get("filename", "app.log")

    fh = RotatingFileHandler(
        log_file,
        maxBytes=config.get("maxBytes", 5 * 1024 * 1024),  # 5MB
        backupCount=config.get("backupCount", 3),
        encoding="utf-8",
    )
    fh.setLevel(config.get("file_level", logging.DEBUG))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Colorlog handler (optional)
    if config.get("colored_console", False) and colorlog is not None:
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        ch.setFormatter(console_formatter)
