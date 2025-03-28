"""Logging configuration module."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta

import colorlog

from dewey.core.base_script import BaseScript


class LoggingConfigurator(BaseScript):
    """Configures logging with colored console output and file rotation.

    Inherits from BaseScript to utilize standardized configuration and logging.
    """

    def __init__(self) -> None:
        """Initializes the LoggingConfigurator, setting the configuration section."""
        super().__init__(config_section="logging")

    def run(self) -> None:
        """Configures logging based on the provided configuration.

        This method sets up the logger with colored console output, file rotation,
        and configurable log levels and formats.
        """
        config = self.config

        self.logger.setLevel(self.get_config_value("level", logging.INFO))

        formatter = logging.Formatter(
            self.get_config_value(
                "format", "%(asctime)s - %(levelname)s - %(message)s"
            )
        )
        self.formatter = formatter  # Store formatter for use in _configure_rotating_handler

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.get_config_value("console_level", logging.INFO))
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # File handler
        log_dir = Path(self.get_config_value("root_dir", "logs"))
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / self.get_config_value("filename", "app.log")

        fh = self._configure_rotating_handler(log_file)
        self.logger.addHandler(fh)

        # Colorlog handler (optional)
        if self.get_config_value("colored_console", False):
            console_formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            ch.setFormatter(console_formatter)

        # Clean up old logs
        retention_days = self.get_config_value("retention_days", 3)
        self._cleanup_old_logs(log_dir, retention_days)

    def _configure_rotating_handler(self, log_file: Path) -> RotatingFileHandler:
        """Configure rotating file handler with retention settings."""
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.get_config_value("maxBytes", 10 * 1024 * 1024),  # 10MB
            backupCount=self.get_config_value("backupCount", 5),
            encoding="utf-8",
        )
        handler.setFormatter(self.formatter)
        return handler

    def _cleanup_old_logs(self, log_dir: Path, retention_days: int) -> None:
        """Delete log files older than retention_days."""
        now = datetime.now()
        cutoff = now - timedelta(days=retention_days)

        for log_file in log_dir.glob("**/*.log"):  # Recursive search
            if log_file.is_file() and datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                try:
                    log_file.unlink()
                    self.logger.info(f"Removed old log file: {log_file}")
                except Exception as e:
                    self.logger.error(f"Error removing {log_file}: {e}")


def configure_logging(config: dict) -> None:
    """Configure logging with colored console output and file rotation.
    
    This function provides a simpler interface for setting up logging without
    requiring a BaseScript instance.
    
    Args:
        config: A dictionary containing logging configuration options
    """
    logger = logging.getLogger()
    logger.setLevel(config.get("level", logging.INFO))

    formatter = logging.Formatter(config.get("format", "%(asctime)s - %(levelname)s - %(message)s"))

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(config.get("console_level", logging.INFO))
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    log_dir = Path("logs")
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
    if config.get("colored_console", False):
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        ch.setFormatter(console_formatter)
