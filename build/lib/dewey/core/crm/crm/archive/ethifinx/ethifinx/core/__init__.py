"""
Core Module
==========

Core functionality for the EthiFinX platform.

Components:
----------
- Config: Configuration management
- Logger: Logging setup and configuration
- API Client: Base API client functionality
"""

from .api_client import APIClient
from .config import Config
from .logger import setup_logger

__all__ = [
    "Config",
    "setup_logger",
    "APIClient",
]
