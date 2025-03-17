"""Tests for the logging configuration module."""

import logging
import os
from pathlib import Path
import pytest
from dewey.config.logging import configure_logging

@pytest.fixture
def log_config():
    """Fixture providing a basic logging configuration."""
    return {
        "level": logging.INFO,
        "format": "%(asctime)s - %(levelname)s - %(message)s",
        "filename": "test.log",
        "maxBytes": 1024,
        "backupCount": 2,
        "colored_console": True
    }

@pytest.fixture
def cleanup_logs():
    """Fixture to clean up log files after tests."""
    yield
    log_dir = Path("logs")
    if log_dir.exists():
        for log_file in log_dir.glob("*.log*"):
            log_file.unlink()
        log_dir.rmdir()

class TestLogging:
    """Test cases for logging configuration."""

    def test_configure_logging_basic(self, log_config, cleanup_logs):
        """Test basic logging configuration."""
        configure_logging(log_config)
        logger = logging.getLogger()
        
        # Check logger level
        assert logger.level == logging.INFO
        
        # Check handlers
        assert len(logger.handlers) > 0
        
        # Verify log directory creation
        log_dir = Path("logs")
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_configure_logging_file_rotation(self, log_config, cleanup_logs):
        """Test log file rotation."""
        configure_logging(log_config)
        logger = logging.getLogger()
        
        # Find the RotatingFileHandler
        rotating_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                rotating_handler = handler
                break
        
        assert rotating_handler is not None
        assert rotating_handler.maxBytes == 1024
        assert rotating_handler.backupCount == 2

    def test_configure_logging_formatters(self, log_config, cleanup_logs):
        """Test log formatters configuration."""
        configure_logging(log_config)
        logger = logging.getLogger()
        
        for handler in logger.handlers:
            formatter = handler.formatter
            assert formatter is not None
            if isinstance(handler, logging.StreamHandler):
                # Check if using colorlog formatter when colored_console is True
                assert "ColoredFormatter" in str(type(formatter))
            else:
                # Check standard formatter for file handler
                assert isinstance(formatter, logging.Formatter)

    def test_configure_logging_custom_levels(self, log_config, cleanup_logs):
        """Test custom logging levels configuration."""
        log_config["level"] = logging.DEBUG
        log_config["console_level"] = logging.WARNING
        log_config["file_level"] = logging.ERROR
        
        configure_logging(log_config)
        logger = logging.getLogger()
        
        assert logger.level == logging.DEBUG
        
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                assert handler.level == logging.WARNING
            elif isinstance(handler, logging.FileHandler):
                assert handler.level == logging.ERROR

    def test_configure_logging_without_color(self, log_config, cleanup_logs):
        """Test logging configuration without colored output."""
        log_config["colored_console"] = False
        configure_logging(log_config)
        logger = logging.getLogger()
        
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                assert isinstance(handler.formatter, logging.Formatter)
                assert "ColoredFormatter" not in str(type(handler.formatter))

    def test_log_file_creation(self, log_config, cleanup_logs):
        """Test log file creation and writing."""
        configure_logging(log_config)
        logger = logging.getLogger()
        
        test_message = "Test log message"
        logger.info(test_message)
        
        log_file = Path("logs") / log_config["filename"]
        assert log_file.exists()
        
        with open(log_file, "r") as f:
            content = f.read()
            assert test_message in content 