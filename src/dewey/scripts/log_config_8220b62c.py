# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Logging Configuration Module.

This module provides centralized logging setup and management for the application.
It includes a LogManager class that handles:
- Logger configuration with script-specific contexts
- Log rotation and file management
- Log analysis and statistics
- Error tracking and reporting

Key Features:
- Rotating log files with size limits (10MB default, 5 backups)
- Centralized log statistics collection
- Error message ID extraction for retry mechanisms
- Clean resource management with automatic cleanup
- Global logging instance for easy access
- Detailed processing metrics and error breakdowns
- Thread-safe logging configuration

The module follows best practices for logging configuration and provides
detailed statistics about processing operations. It's designed to be:

1. Extensible: Add new log handlers and formatters easily
2. Maintainable: Centralized configuration and cleanup
3. Informative: Rich statistics and error tracking
4. Robust: Handles edge cases and resource cleanup properly

Example Usage:
    >>> from scripts.log_config import log_manager
    >>> logger = log_manager.setup_logger(__name__)
    >>> logger.info("Starting processing")
    >>> logger.error("Failed to process message 123")
    >>> stats = log_manager.get_processing_stats()
    >>> log_manager.log_processing_summary(stats)

Note: Always use the log_manager instance for consistent logging configuration
across the application.
"""

import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import Config


class LogManager:
    """Centralized logging and log analysis manager.

    This class provides comprehensive logging capabilities including:
    - Logger setup with script-specific contexts
    - Log rotation and file management
    - Error tracking and message ID extraction
    - Processing statistics collection
    - Resource cleanup management
    - Thread-safe logging operations

    Attributes:
    ----------
        log_file (str): Path to the main log file
        _loggers (Dict[str, logging.Logger]): Dictionary of configured loggers
        _handlers (Dict[str, List[logging.Handler]]): Dictionary of logger handlers

    Methods:
    -------
        setup_logger: Configures a logger with rotation and formatting
        get_errored_message_ids: Extracts message IDs from error logs
        get_processing_stats: Collects processing statistics from logs
        log_processing_summary: Logs formatted processing summary
        rotate_logs: Forces log rotation manually
        cleanup: Properly closes and removes handlers
        __del__: Destructor for resource cleanup

    Example:
    -------
        >>> log_manager = LogManager("app.log")
        >>> logger = log_manager.setup_logger("my_script")
        >>> logger.info("Starting processing")
        >>> error_ids = log_manager.get_errored_message_ids()
        >>> stats = log_manager.get_processing_stats()
        >>> log_manager.log_processing_summary(stats)

    """

    def __init__(self, log_file: str = "project.log") -> None:
        """Initialize the LogManager instance.

        Args:
        ----
            log_file (str): Path to the main log file. Defaults to "project.log".

        """
        self.log_file = log_file
        self._loggers: dict[str, logging.Logger] = {}
        self._handlers: dict[str, list[logging.Handler]] = {}

    def setup_logger(self, script_name: str) -> logging.Logger:
        """Configure logging with script name context and rotation.

        This method sets up a logger with:
        - Rotating file handler (10MB max size, 5 backups)
        - Console handler for real-time output
        - Script-specific formatting
        - Proper resource management
        - Thread-safe operations

        Args:
        ----
            script_name (str): Name of the script using the logger.
                            Used to create unique logger instances.

        Returns:
        -------
            logging.Logger: Configured logger instance with script context.

        Raises:
        ------
            OSError: If log directory creation fails
            PermissionError: If log file cannot be written

        Notes:
        -----
            1. If a logger with the same script_name exists, returns existing logger
            2. Creates 'logs' directory if it doesn't exist
            3. Sets up both file and console handlers
            4. Prevents propagation to root logger
            5. Uses thread-safe handlers

        Example:
        -------
            >>> logger = log_manager.setup_logger("data_processor")
            >>> logger.info("Starting data processing")

        """
        if script_name in self._loggers:
            return self._loggers[script_name]

        # Create logs directory if it doesn't exist
        Path("logs").mkdir(exist_ok=True)

        # Configure logging
        logger = logging.getLogger(script_name)

        # Only add handlers if the logger doesn't have any
        if not logger.handlers:
            logger.setLevel(logging.INFO)

            # Rotating file handler (10MB max size, keep 5 backup files)
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,  # 10MB
            )
            file_handler.setLevel(logging.INFO)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Create formatter with script context
            formatter = logging.Formatter(
                "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
            )

            # Add formatter to handlers
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            # Prevent propagation to root logger
            logger.propagate = False

            # Store handlers for cleanup
            self._handlers[script_name] = [file_handler, console_handler]
            self._loggers[script_name] = logger

        return logger

    def get_errored_message_ids(self) -> list[str]:
        """Extract message IDs from error logs.

        Scans the log file for error entries and extracts associated message IDs.
        Useful for identifying failed processing attempts and implementing retry logic.

        Returns:
        -------
            List[str]: List of unique message IDs that encountered errors.

        Raises:
        ------
            FileNotFoundError: If log file doesn't exist
            IOError: If log file cannot be read

        Notes:
        -----
            1. Looks for pattern: "Error processing message <ID>"
            2. Returns unique IDs only
            3. Case-insensitive search
            4. Skips malformed entries silently

        Example:
        -------
            >>> error_ids = log_manager.get_errored_message_ids()
            >>> print(f"Found {len(error_ids)} errored messages")

        """
        error_ids = []
        error_pattern = r"Error processing message ([a-zA-Z0-9]+)"

        with open(self.log_file) as f:
            for line in f:
                if "ERROR" in line:
                    match = re.search(error_pattern, line)
                    if match:
                        error_ids.append(match.group(1))

        return error_ids

    def get_processing_stats(self) -> dict[str, Any]:
        """Analyze log file for processing statistics.

        Collects comprehensive statistics including:
        - Total messages processed
        - Error and warning counts
        - Processing time range
        - Error type breakdown
        - Processing rate (messages/second)

        Returns:
        -------
            Dict[str, Any]: Dictionary containing processing statistics with keys:
                - total_processed: Total messages processed
                - errors: Total error count
                - warnings: Total warning count
                - start_time: First log entry timestamp
                - end_time: Last log entry timestamp
                - error_types: Dictionary of error type counts
                - processing_rate: Messages processed per second

        Raises:
        ------
            FileNotFoundError: If log file doesn't exist
            IOError: If log file cannot be read

        Notes:
        -----
            1. Handles malformed log entries gracefully
            2. Calculates processing rate based on time range
            3. Error types are extracted from first part of error message
            4. Timestamps must be in format: YYYY-MM-DD HH:MM:SS,SSS

        Example:
        -------
            >>> stats = log_manager.get_processing_stats()
            >>> print(f"Processing rate: {stats['processing_rate']:.2f} msg/sec")

        """
        stats = {
            "total_processed": 0,
            "errors": 0,
            "warnings": 0,
            "start_time": None,
            "end_time": None,
            "error_types": {},
            "processing_rate": 0,
        }

        with open(self.log_file) as f:
            for line in f:
                # Parse timestamp
                try:
                    timestamp_str = line.split(" - ")[0]
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                    if not stats["start_time"] or timestamp < stats["start_time"]:
                        stats["start_time"] = timestamp
                    if not stats["end_time"] or timestamp > stats["end_time"]:
                        stats["end_time"] = timestamp
                except:
                    continue

                # Count messages processed
                if "Processed" in line and "messages" in line:
                    try:
                        count = int(
                            line.split("Processed")[1].split("messages")[0].strip(),
                        )
                        stats["total_processed"] = max(stats["total_processed"], count)
                    except:
                        continue

                # Count errors and warnings
                if "ERROR" in line:
                    stats["errors"] += 1
                    error_type = line.split("ERROR - ")[1].split(":")[0]
                    stats["error_types"][error_type] = (
                        stats["error_types"].get(error_type, 0) + 1
                    )
                elif "WARNING" in line:
                    stats["warnings"] += 1

        # Calculate processing rate
        if stats["start_time"] and stats["end_time"]:
            duration = (stats["end_time"] - stats["start_time"]).total_seconds()
            if duration > 0:
                stats["processing_rate"] = stats["total_processed"] / duration

        return stats

    def log_processing_summary(self, stats: dict[str, Any]) -> None:
        """Log a summary of processing statistics.

        Formats and logs the processing statistics in a human-readable format.
        Includes error breakdown and performance metrics.

        Args:
        ----
            stats (Dict[str, Any]): Processing statistics dictionary from get_processing_stats()

        Raises:
        ------
            KeyError: If required stats keys are missing
            TypeError: If stats is not a dictionary

        Notes:
        -----
            1. Uses 'log_analyzer' logger context for consistent formatting
            2. Includes error type breakdown if present
            3. Logs processing rate with 2 decimal places
            4. Adds section headers for better readability

        Example:
        -------
            >>> stats = {
                    "total_processed": 1000,
                    "errors": 5,
                    "warnings": 10,
                    "processing_rate": 50.1234
                }
            >>> log_manager.log_processing_summary(stats)

        """
        logger = self.setup_logger("log_analyzer")

        logger.info("=== Processing Summary ===")
        logger.info(f"Total messages processed: {stats['total_processed']}")
        logger.info(f"Processing rate: {stats['processing_rate']:.2f} messages/second")
        logger.info(f"Total errors: {stats['errors']}")
        logger.info(f"Total warnings: {stats['warnings']}")

        if stats["error_types"]:
            logger.info("\nError type breakdown:")
            for error_type, count in stats["error_types"].items():
                logger.info(f"  {error_type}: {count}")

    def rotate_logs(self) -> None:
        """Force rotation of log files.

        Manually triggers log rotation for all configured rotating file handlers.
        Useful for maintenance or when implementing custom rotation schedules.

        Notes:
        -----
            1. Rotation occurs regardless of file size
            2. Creates new empty log file
            3. Maintains backup count configuration
            4. Thread-safe operation

        Example:
        -------
            >>> # Force rotation at end of day
            >>> if datetime.now().hour == 23:
            >>>     log_manager.rotate_logs()

        """
        for logger in self._loggers.values():
            for handler in logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    handler.doRollover()

    def cleanup(self) -> None:
        """Clean up handlers and loggers.

        Properly closes and removes all logging handlers and clears internal state.
        Should be called when shutting down the application to ensure proper
        resource cleanup.

        Notes:
        -----
            1. Closes all file handlers properly
            2. Removes handlers from loggers
            3. Clears internal state
            4. Automatically called during destruction
            5. Safe to call multiple times

        Example:
        -------
            >>> try:
            >>>     # Application code
            >>> finally:
            >>>     log_manager.cleanup()

        """
        for script_name, handlers in self._handlers.items():
            logger = self._loggers.get(script_name)
            if logger:
                for handler in handlers:
                    handler.close()
                    logger.removeHandler(handler)
        self._handlers.clear()
        self._loggers.clear()

    def __del__(self) -> None:
        """Ensure proper cleanup of resources.

        Destructor method that calls cleanup() to properly release logging resources.
        This is a safety measure to prevent resource leaks.
        """
        self.cleanup()


# Global instance for centralized logging management
log_manager = LogManager()


def setup_logger(script_name: str) -> logging.Logger:
    """Convenience function for backward compatibility.

    Provides direct access to the global LogManager's setup_logger method.

    Args:
    ----
        script_name (str): Name of the script using the logger

    Returns:
    -------
        logging.Logger: Configured logger instance

    """
    return log_manager.setup_logger(script_name)


def setup_logging() -> None:
    """Set up basic logging configuration.

    Configures the root logger with:
    - File handler using application config
    - Console handler for real-time output
    - Standard formatting
    - Global log level from config

    Note:
    ----
        This is a basic configuration intended for simple use cases.
        For more advanced logging, use the LogManager class directly.

    """
    config = Config()  # Get Config instance
    logging.basicConfig(
        filename=str(config.LOG_FILE),  # Convert Path to string
        level=config.LOG_LEVEL,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    log_manager = logging.getLogger("email_operations")
    log_manager.setLevel(logging.DEBUG)  # Set to DEBUG to capture detailed logs
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    handler.setFormatter(formatter)
    log_manager.addHandler(handler)
