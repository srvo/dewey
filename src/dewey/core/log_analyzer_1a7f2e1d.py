#!/usr/bin/env python3
"""Mercury Import Log Analyzer.

Monitors mercury_import.log and maintains an error status report.
Uses external deepinfra_client.py for API interactions.
"""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Configuration
LOG_FILE = Path("/Users/srvo/books/logs/mercury_import.log")
STATE_FILE = LOG_FILE.with_name(LOG_FILE.name + ".state")
ERROR_REPORT = Path("mercury_import_errors.md")
CHECK_INTERVAL = 5  # Seconds between log checks

# Create global logger
logger = logging.getLogger(__name__)


@dataclass
class ErrorClassificationConfig:
    """Configuration for error classification."""

    log_file: Path = LOG_FILE
    state_file: Path = STATE_FILE
    error_report: Path = ERROR_REPORT
    check_interval: int = CHECK_INTERVAL


@dataclass
class ClassifiedError:
    """Represents a classified error with tracking information."""

    error_type: str
    description: str
    resolution: str
    components: str
    example: str
    error_hash: str
    first_occurrence: str
    last_seen: str
    count: int


def classify_errors(
    config: ErrorClassificationConfig,
    log_lines: list[str],
) -> list[ClassifiedError]:
    """Classify errors using external deepinfra_client.py.

    Args:
    ----
        config: The error classification configuration.
        log_lines: A list of log lines to classify.

    Returns:
    -------
        A list of classified errors.

    """
    if not log_lines:
        logger.debug("No log lines to classify")
        return []

    try:
        # Call external script with log lines via stdin
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "deepinfra_client.py")],
            input="\n".join(log_lines),
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse JSON output from script
        raw_errors = json.loads(result.stdout)
        return [ClassifiedError(**e) for e in raw_errors]

    except subprocess.CalledProcessError as e:
        logger.exception("DeepInfra client failed: %s", e.stderr)
        return []
    except json.JSONDecodeError:
        logger.exception("Invalid JSON response from deepinfra_client")
        return []
    except Exception as e:
        logger.exception("Classification failed: %s", str(e))
        return []


def update_error_registry(
    existing_errors: dict[str, ClassifiedError],
    new_errors: list[ClassifiedError],
) -> dict[str, ClassifiedError]:
    """Update error registry with new errors, merging duplicates.

    Args:
    ----
        existing_errors: A dictionary of existing errors, keyed by error hash.
        new_errors: A list of new errors to add to the registry.

    Returns:
    -------
        An updated dictionary of errors.

    """
    current_time = time.strftime("%Y-%m-%d %H:%M")
    for error in new_errors:
        if error.error_hash in existing_errors:
            existing = existing_errors[error.error_hash]
            existing.count += 1
            existing.last_seen = current_time
        else:
            error.first_occurrence = current_time
            error.last_seen = current_time
            existing_errors[error.error_hash] = error
    return existing_errors


def generate_error_report(errors: list[ClassifiedError], report_file: Path) -> None:
    """Generate markdown error report from classified errors.

    Args:
    ----
        errors: A list of classified errors.
        report_file: The path to the error report file.

    """
    if not errors:
        report_file.write_text("# No errors found\n")
        return

    report = [
        "# Mercury Import Error Report\n",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}\n",
    ]
    report.append(
        "| Type | Description | Resolution | Components | Example | First Seen | Last Seen | Count |\n",
    )
    report.append(
        "|------|-------------|------------|------------|---------|------------|-----------|-------|\n",
    )

    for error in sorted(errors, key=lambda x: x.count, reverse=True):
        report.append(
            f"| {error.error_type} | {error.description} | {error.resolution} | "
            f"{error.components} | `{error.example}` | {error.first_occurrence} | "
            f"{error.last_seen} | {error.count} |\n",
        )

    report_file.write_text("".join(report))
    logger.info("Updated error report at %s", report_file)


def load_existing_errors(state_file: Path) -> dict[str, ClassifiedError]:
    """Load existing errors from the state file.

    Args:
    ----
        state_file: The path to the state file.

    Returns:
    -------
        A dictionary of existing errors, keyed by error hash.

    """
    existing_errors: dict[str, ClassifiedError] = {}

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            existing_errors = {e["error_hash"]: ClassifiedError(**e) for e in state}
            logger.info(
                "Loaded %d existing errors from state file",
                len(existing_errors),
            )
        except json.JSONDecodeError:
            logger.exception("Failed to load state file, starting fresh")
    return existing_errors


def check_for_new_errors(
    config: ErrorClassificationConfig,
    existing_errors: dict[str, ClassifiedError],
) -> list[ClassifiedError]:
    """Check for new errors in the log file.

    Args:
    ----
        config: The error classification configuration.
        existing_errors: A dictionary of existing errors, keyed by error hash.

    Returns:
    -------
        A list of new classified errors.

    """
    # Dummy implementation - replace with actual log parsing logic
    # This example simulates finding a new error every few iterations
    return classify_errors(config, ["Sample log line for error classification"])


def monitor_logs(config: ErrorClassificationConfig) -> None:
    """Main monitoring loop with error state persistence.

    Args:
    ----
        config: The error classification configuration.

    """
    existing_errors = load_existing_errors(config.state_file)

    try:
        while True:
            new_errors = check_for_new_errors(config, existing_errors)
            if new_errors:
                existing_errors = update_error_registry(existing_errors, new_errors)
                generate_error_report(
                    list(existing_errors.values()),
                    config.error_report,
                )
                config.state_file.write_text(
                    json.dumps([e.__dict__ for e in existing_errors.values()]),
                )
                logger.info("Processed %d new errors", len(new_errors))
            time.sleep(config.check_interval)
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")


def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = ErrorClassificationConfig()
    try:
        monitor_logs(config)
    except Exception as e:
        logger.critical("Fatal error in monitor: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
