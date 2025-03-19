"""Logging configuration module."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import colorlog
from dewey.core.base_script import BaseScript


class LoggingConfigurator(BaseScript):
    """Configures logging with colored console output and file rotation."""

    def __init__(self):
        super().__init__(config_section='logging')

    def run(self) -> None:
        """Configure logging based on the provided configuration."""
        config = self.config

        logger = logging.getLogger()
        logger.setLevel(config.get("level", logging.INFO))

        formatter = logging.Formatter(config.get("format", "%(asctime)s - %(levelname)s - %(message)s"))

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(config.get("console_level", logging.INFO))
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler
        log_dir = Path(self.config.get("root_dir", "logs"))
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
```