"""Logging configuration module."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional, Union

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

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.get_config_value("console_level", logging.INFO))
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # File handler
        log_dir = Path(self.get_config_value("root_dir", "logs"))
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / self.get_config_value("filename", "app.log")

        fh = RotatingFileHandler(
            log_file,
            maxBytes=self.get_config_value("maxBytes", 5 * 1024 * 1024),  # 5MB
            backupCount=self.get_config_value("backupCount", 3),
            encoding="utf-8",
        )
        fh.setLevel(self.get_config_value("file_level", logging.DEBUG))
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # Colorlog handler (optional)
        if self.get_config_value("colored_console", False):
            console_formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            ch.setFormatter(console_formatter)


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
