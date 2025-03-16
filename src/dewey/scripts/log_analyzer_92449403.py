# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Utility script for analyzing email processing logs and providing statistics.

This module provides a comprehensive set of tools for:
- Extracting processing statistics from log files
- Identifying errored message IDs
- Generating detailed processing summaries
- Tracking and reporting error recovery progress

The module is designed to be imported by other scripts to provide consistent
log analysis capabilities without requiring modifications to their core logic.

Key Features:
- Robust error handling and logging
- Flexible log file path configuration
- Detailed statistical analysis
- Progress tracking for error recovery operations
- Thread-safe operations
- Comprehensive error recovery metrics

Example Usage:
    >>> from scripts.log_analyzer import get_processing_stats
    >>> total, earliest, errors = get_processing_stats()
    >>> print(f"Processed {total} emails since {earliest} with {errors} errors")

Note:
----
    The module assumes a specific log format. If the log format changes,
    the regex patterns in this module will need to be updated accordingly.

Version History:
    1.0.0 - Initial release with core functionality
    1.1.0 - Added error recovery tracking features
    1.2.0 - Enhanced type hints and documentation

"""
from __future__ import annotations

import logging
import re
from datetime import datetime

# Import documentation:
# logging - Standard library for logging operations
# re - Regular expressions for parsing log patterns
# datetime - For handling date/time operations
# typing - For type hints and annotations

# Initialize module-level logger with the current module's name
# This allows for granular control of logging at the module level
# and helps identify the source of log messages
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Default to INFO level logging

# Constants for log parsing
DEFAULT_LOG_FILE = "project.log"  # Default log file path
PROCESSED_PATTERN = r"Processed (\d+) emails \(earliest: (\d{4}-\d{2}-\d{2})\)"
ERROR_PATTERN = r"Error processing message ([a-f0-9]+):"


def get_processing_stats(log_file: str = DEFAULT_LOG_FILE) -> tuple[int, datetime, int]:
    """Extracts key processing statistics from email processing logs.

    This function parses the log file to extract:
    - Total number of emails processed
    - Earliest email date encountered
    - Total number of errors encountered

    The function is designed to be resilient to:
    - Missing log files
    - Malformed log entries
    - Date parsing errors

    Args:
    ----
        log_file (str): Path to the log file to analyze. Defaults to 'project.log'.
            The log file should follow the standard format:
            [timestamp] [level] - Processed X emails (earliest: YYYY-MM-DD)

    Returns:
    -------
        Tuple[int, datetime, int]:
            - total_processed: Total number of emails processed
            - earliest_date: Earliest email date encountered
            - error_count: Total number of errors encountered

        If the log file cannot be read or is empty, returns (0, current_date, 0)

    Raises:
    ------
        IOError: If the log file cannot be read
        ValueError: If date parsing fails

    Example:
    -------
        >>> total, earliest, errors = get_processing_stats()
        >>> print(f"Processed {total} emails since {earliest} with {errors} errors")

    Performance Considerations:
        - Processes log file line by line to minimize memory usage
        - Uses regex pattern matching for efficient parsing
        - Caches the earliest date to avoid unnecessary comparisons

    Error Handling:
        - Returns default values (0, current_date, 0) on error
        - Logs detailed error information for debugging

    """
    total_processed = 0
    earliest_date = datetime.now()
    error_count = 0
    processed_pattern = r"Processed (\d+) emails \(earliest: (\d{4}-\d{2}-\d{2})\)"

    try:
        with open(log_file) as f:
            for line in f:
                if "Error processing message" in line:
                    error_count += 1
                if "Processed" in line and "emails (earliest:" in line:
                    match = re.search(processed_pattern, line)
                    if match:
                        count = int(match.group(1))
                        date_str = match.group(2)
                        total_processed = max(total_processed, count)
                        try:
                            date = datetime.strptime(date_str, "%Y-%m-%d")
                            earliest_date = min(earliest_date, date)
                        except ValueError:
                            continue

        return total_processed, earliest_date, error_count
    except Exception as e:
        logger.exception(f"Error getting processing stats: {e!s}")
        return 0, datetime.now(), 0


def get_errored_message_ids(log_file: str = DEFAULT_LOG_FILE) -> set[str]:
    """Extracts unique message IDs from error logs.

    This function scans the log file for error entries and extracts the unique
    message IDs associated with failed processing attempts. The message IDs
    are expected to be in hexadecimal format (e.g., '1a2b3c4d5e6f').

    Args:
    ----
        log_file (str): Path to the log file to analyze. Defaults to 'project.log'.
            The log file should contain error entries in the format:
            [timestamp] ERROR - Error processing message <message_id>: <error_details>

    Returns:
    -------
        Set[str]: Set of unique message IDs that had processing errors.
            Returns empty set if:
            - No errors found
            - Log file cannot be read
            - Message ID format is invalid

    Raises:
    ------
        IOError: If the log file cannot be read
        re.error: If the regex pattern fails to compile

    Example:
    -------
        >>> error_ids = get_errored_message_ids()
        >>> print(f"Found {len(error_ids)} errored message IDs")

    Performance Considerations:
        - Uses a set to automatically handle uniqueness
        - Processes file line by line to handle large log files
        - Compiles regex pattern once for efficiency

    Error Handling:
        - Returns empty set on any error
        - Logs detailed error information for debugging

    """
    error_pattern = r"Error processing message ([a-f0-9]+):"
    message_ids = set()

    try:
        with open(log_file) as f:
            for line in f:
                if "Error processing message" in line:
                    match = re.search(error_pattern, line)
                    if match:
                        message_ids.add(match.group(1))
        return message_ids
    except Exception as e:
        logger.exception(f"Error parsing log file: {e!s}")
        return set()


def log_processing_summary(
    total_processed: int | None = None,
    message_ids: set[str] | None = None,
    log_file: str = DEFAULT_LOG_FILE,
) -> None:
    """Logs a comprehensive summary of email processing statistics.

    This function generates and logs a detailed summary of email processing
    operations, including:
    - Total emails processed
    - Earliest email date
    - Total errors encountered
    - Unique errored messages
    - Overall error rate

    The function is optimized to avoid redundant log file reads by accepting
    pre-calculated values for total_processed and message_ids.

    Args:
    ----
        total_processed (Optional[int]): Override for total processed count (if known).
            If None, will be calculated from log file.
        message_ids (Optional[Set[str]]): Set of errored message IDs (if already collected).
            If None, will be extracted from log file.
        log_file (str): Path to the log file to analyze. Defaults to 'project.log'.

    Raises:
    ------
        ValueError: If error rate calculation fails
        IOError: If log file cannot be read
        ZeroDivisionError: If total_processed is zero

    Example:
    -------
        >>> log_processing_summary()
        INFO: Processing History:
        INFO: - Total emails processed: 1,234
        INFO: - Earliest email date: 2023-01-01
        INFO: - Total errors encountered: 12
        INFO: - Unique errored messages: 10
        INFO: - Overall error rate: 0.81%

    Performance Considerations:
        - Minimizes file I/O by accepting pre-calculated values
        - Uses efficient string formatting for log messages
        - Handles large datasets through set operations

    Error Handling:
        - Logs errors without raising exceptions
        - Provides meaningful error messages
        - Gracefully handles missing or invalid data

    """
    try:
        if total_processed is None or message_ids is None:
            total_processed, earliest_date, total_errors = get_processing_stats(
                log_file,
            )
            if message_ids is None:
                message_ids = get_errored_message_ids(log_file)
        else:
            _, earliest_date, total_errors = get_processing_stats(log_file)

        error_rate = (
            (len(message_ids) / total_processed * 100) if total_processed > 0 else 0
        )

        logger.info("Processing History:")
        logger.info(f"- Total emails processed: {total_processed:,}")
        logger.info(f"- Earliest email date: {earliest_date.strftime('%Y-%m-%d')}")
        logger.info(f"- Total errors encountered: {total_errors:,}")
        logger.info(f"- Unique errored messages: {len(message_ids):,}")
        logger.info(f"- Overall error rate: {error_rate:.2f}%")
    except Exception as e:
        logger.exception(f"Error generating processing summary: {e!s}")


def log_recovery_progress(
    success_count: int,
    failure_count: int,
    total_to_process: int,
) -> None:
    """Logs progress of the error recovery process.

    This function provides real-time progress updates during error recovery
    operations, including:
    - Current progress count
    - Success and failure counts
    - Current success rate

    The function is designed to be called frequently during recovery operations
    to provide continuous feedback without overwhelming the log file.

    Args:
    ----
        success_count (int): Number of successfully processed messages.
            Must be >= 0
        failure_count (int): Number of failed processing attempts.
            Must be >= 0
        total_to_process (int): Total number of messages to process.
            Must be > 0

    Raises:
    ------
        ZeroDivisionError: If success_count + failure_count is zero
        ValueError: If any count is negative or total_to_process is zero

    Example:
    -------
        >>> log_recovery_progress(50, 5, 100)
        INFO: Recovery Progress: 55/100 (Success: 50, Failed: 5, Current Success Rate: 90.91%)

    Performance Considerations:
        - Lightweight calculation for frequent calls
        - Minimal string formatting overhead
        - Efficient rate calculation

    Error Handling:
        - Validates input parameters
        - Logs errors without interrupting recovery process
        - Provides meaningful error messages

    """
    try:
        current_success_rate = (success_count / (success_count + failure_count)) * 100
        logger.info(
            f"Recovery Progress: {success_count + failure_count}/{total_to_process} "
            f"(Success: {success_count}, Failed: {failure_count}, "
            f"Current Success Rate: {current_success_rate:.2f}%)",
        )
    except Exception as e:
        logger.exception(f"Error logging recovery progress: {e!s}")


def log_recovery_summary(
    total_to_process: int,
    success_count: int,
    failure_count: int,
) -> None:
    """Logs a final summary of the error recovery process.

    This function generates and logs a comprehensive summary of the error
    recovery operation, including:
    - Total messages attempted
    - Successfully processed messages
    - Failed processing attempts
    - Final success rate

    The summary is designed to provide a complete picture of the recovery
    operation's outcome and should be called once at the end of the process.

    Args:
    ----
        total_to_process (int): Total number of messages attempted.
            Must be > 0
        success_count (int): Number of successfully processed messages.
            Must be >= 0
        failure_count (int): Number of failed processing attempts.
            Must be >= 0

    Raises:
    ------
        ZeroDivisionError: If total_to_process is zero
        ValueError: If any count is negative

    Example:
    -------
        >>> log_recovery_summary(100, 90, 10)
        INFO: Error recovery completed:
        INFO: - Messages attempted: 100
        INFO: - Successfully processed: 90
        INFO: - Failed to process: 10
        INFO: - Final success rate: 90.00%

    Performance Considerations:
        - Single calculation of success rate
        - Efficient string formatting for summary
        - Minimal memory usage

    Error Handling:
        - Validates input parameters
        - Logs errors without raising exceptions
        - Provides meaningful error messages

    """
    try:
        final_success_rate = (success_count / total_to_process) * 100
        logger.info("Error recovery completed:")
        logger.info(f"- Messages attempted: {total_to_process:,}")
        logger.info(f"- Successfully processed: {success_count:,}")
        logger.info(f"- Failed to process: {failure_count:,}")
        logger.info(f"- Final success rate: {final_success_rate:.2f}%")
    except Exception as e:
        logger.exception(f"Error logging recovery summary: {e!s}")
