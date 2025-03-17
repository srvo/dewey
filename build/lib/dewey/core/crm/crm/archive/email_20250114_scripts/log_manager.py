"""Centralized logging configuration and management.
Combines functionality from log_config.py and log_manager.py.
"""

import logging
import logging.handlers
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional

from scripts.config import Config


class LogManager:
    """Manages logging configuration, rotation, and analysis."""

    def __init__(
        self,
        log_path: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ):
        """Initialize log manager with config values.

        Args:
        ----
            log_path: Path to log file. If not provided, uses Config.LOG_FILE
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep

        """
        self.config = Config()
        self.log_path = Path(log_path) if log_path else Path(self.config.LOG_FILE)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: Dict[str, List[logging.Handler]] = {}
        self.handler = None
        self.logger = self.setup_logger(__name__)

    def setup_logger(self, script_name: str) -> logging.Logger:
        """Configure logging with script name context and rotation."""
        if script_name in self._loggers:
            return self._loggers[script_name]

        # Create logs directory if it doesn't exist
        self.log_path.parent.mkdir(exist_ok=True)

        # Configure logging
        logger = logging.getLogger(script_name)

        # Only add handlers if the logger doesn't have any
        if not logger.handlers:
            logger.setLevel(logging.INFO)

            # Rotating file handler
            file_handler = RotatingFileHandler(
                str(self.log_path),
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
            )
            file_handler.setLevel(logging.INFO)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Create formatter with script context
            formatter = logging.Formatter(
                "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"
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

    def get_errored_message_ids(self) -> List[str]:
        """Extract message IDs from error logs."""
        error_ids = []
        error_pattern = r"Error processing message ([a-zA-Z0-9]+)"

        with open(self.log_file, "r") as f:
            for line in f:
                if "ERROR" in line:
                    match = re.search(error_pattern, line)
                    if match:
                        error_ids.append(match.group(1))

        return error_ids

    def get_processing_stats(self) -> Dict:
        """Analyze log file for processing statistics."""
        stats = {
            "total_processed": 0,
            "errors": 0,
            "warnings": 0,
            "start_time": None,
            "end_time": None,
            "error_types": {},
            "processing_rate": 0,
        }

        with open(self.log_file, "r") as f:
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
                            line.split("Processed")[1].split("messages")[0].strip()
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

    def log_processing_summary(self, stats: Dict):
        """Log a summary of processing statistics."""
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

    def cleanup(self):
        """Clean up handlers and loggers."""
        for script_name, handlers in self._handlers.items():
            logger = self._loggers.get(script_name)
            if logger:
                for handler in handlers:
                    handler.close()
                    logger.removeHandler(handler)
        self._handlers.clear()
        self._loggers.clear()

    def __del__(self):
        """Ensure proper cleanup of resources."""
        self.cleanup()

    def log_info(self, message: str) -> None:
        """Log an info message.

        Args:
        ----
            message: Message to log

        """
        self.logger.info(message)

    def log_error(self, message: str) -> None:
        """Log an error message.

        Args:
        ----
            message: Message to log

        """
        self.logger.error(message)

    def log_warning(self, message: str) -> None:
        """Log a warning message.

        Args:
        ----
            message: Message to log

        """
        self.logger.warning(message)

    def get_logs(self) -> str:
        """Get contents of current log file.

        Returns:
        -------
            String containing log file contents

        """
        if self.log_path.exists():
            return self.log_path.read_text()
        return ""

    def setup_logging(self):
        logging.basicConfig(
            filename="project.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s:%(message)s",
        )

    def log_fetch_success(self, count):
        logging.info(f"Successfully fetched {count} emails.")

    def log_fetch_failure(self, error):
        logging.error(f"Failed to fetch emails: {error}")

    def log_db_success(self, operation):
        logging.info(f"Database operation successful: {operation}")

    def log_db_failure(self, error):
        logging.error(f"Database operation failed: {error}")
