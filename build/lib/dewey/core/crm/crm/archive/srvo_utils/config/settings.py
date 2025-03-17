"""Application configuration settings.

This module contains all the configuration settings for the email processing
application.

Includes:
- Database connection settings
- Gmail API credentials
- Logging configuration

The settings are loaded from environment variables when available, with sensible
defaults provided for local development.

Attributes:
    BASE_DIR (Path): The base directory of the project, used to construct other paths
    DATABASE_URL (str): Database connection URL
    GMAIL_CREDENTIALS_PATH (Path): Path to Gmail API credentials file
    GMAIL_TOKEN_PATH (Path): Path to store Gmail API token
    LOGGING_CONFIG (dict): Logging configuration dictionary
"""

import os
from pathlib import Path

# Base directory - points to the project root.
# Used to construct absolute paths for other resources.
# This is set to the parent directory of this file's location.
BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
# Uses environment variable if set, otherwise defaults to
# local PostgreSQL instance running on localhost
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/email_processing")

# Gmail API configuration
# Paths to credentials and token files, stored in config directory
GMAIL_CREDENTIALS_PATH = BASE_DIR / "config" / "credentials.json"
GMAIL_TOKEN_PATH = BASE_DIR / "config" / "token.pickle"

# Logging configuration
# Configures both console and file logging with standard format
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(module)s:%(lineno)d - %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "email_processing.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 5,  # 5MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "database": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "email_processing": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
