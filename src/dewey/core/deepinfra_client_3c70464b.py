#!/usr/bin/env python3
"""DeepInfra API Client.

Handles error classification requests through the DeepInfra API with
improved error handling, retries, and chunking for large files.
"""

import hashlib
import logging
import sys
import time
from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
API_KEY = "fA5ctlII2PBQNGHbCxcZzRt3IFkrfFiV"
MAX_RETRIES = 3
RETRY_DELAY = 1.5
CHUNK_SIZE = 1000  # Lines per processing chunk
MAX_TOKENS = 2000  # Conservative token limit for API

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def classify_errors(log_lines: list[str]) -> list[dict[str, Any]]:
    """Classify errors using DeepInfra API with chunking and retry logic."""
    chunks = [
        log_lines[i : i + CHUNK_SIZE] for i in range(0, len(log_lines), CHUNK_SIZE)
    ]
    all_errors = {}

    for idx, chunk in enumerate(chunks):
        logger.info(
            "Processing chunk %d/%d (%d lines)",
            idx + 1,
            len(chunks),
            len(chunk),
        )
        prompt = (
            "Analyze this partial application log and classify errors:\n"
            "For each error, identify:\n"
            "1. Error type/classification\n"
            "2. Brief description\n"
            "3. Potential resolution steps\n"
            "4. Affected components\n"
            "5. Example of the error\n"
            "Format as markdown table. This is PARTIAL LOG - entries may appear in multiple sections.\n\n"
            f"{''.join(chunk)}"
        )

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": MAX_TOKENS,
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()

                response_data = response.json()
                chunk_errors = parse_api_response(response_data)

                for error in chunk_errors:
                    error_hash = error["error_hash"]
                    if error_hash in all_errors:
                        # Update existing error counts and timestamps
                        all_errors[error_hash]["count"] += 1
                        all_errors[error_hash]["last_seen"] = time.strftime(
                            "%Y-%m-%d %H:%M",
                        )
                    else:
                        # Track new error with initial timestamps
                        error["first_occurrence"] = time.strftime("%Y-%m-%d %H:%M")
                        all_errors[error_hash] = error

                break  # Success - move to next chunk
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "API request failed (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(e),
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.exception("Max retries exceeded for API request")
                    return list(all_errors.values())
            except Exception as e:
                logger.exception("Unexpected error during classification: %s", str(e))
                return list(all_errors.values())

        # Rate limit protection between chunks
        if idx < len(chunks) - 1:
            time.sleep(2)

    return list(all_errors.values())


def parse_api_response(response_data: dict) -> list[dict[str, Any]]:
    """Parse API response into structured error data."""
    errors = []
    try:
        if not response_data.get("choices"):
            return errors

        content = response_data["choices"][0]["message"]["content"]
        timestamp = time.strftime("%Y-%m-%d %H:%M")

        for line in content.split("\n"):
            if not line.startswith("|"):
                continue

            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) != 5:
                continue

            errors.append(
                {
                    "error_type": parts[0],
                    "description": parts[1],
                    "resolution": parts[2],
                    "components": parts[3],
                    "example": parts[4][:150],  # Truncate long examples
                    "error_hash": hashlib.md5(line.encode()).hexdigest(),
                    "first_occurrence": timestamp,
                    "last_seen": timestamp,
                    "count": 1,
                },
            )
    except Exception as e:
        logger.exception("Failed to parse API response: %s", str(e))
    return errors


def generate_issues_markdown(
    errors: list[dict[str, Any]],
    output_file: Path = Path("issues.md"),
) -> None:
    """Write classified errors to markdown file with formatted table."""
    if not errors:
        content = "# Error Report\n\nNo issues found 👍"
    else:
        table_header = "| Type | Description | Resolution | Components | Example | First Seen | Last Seen | Count |\n"
        table_separator = "|------|-------------|------------|------------|---------|------------|-----------|-------|\n"
        rows = []

        for error in errors:
            row = (
                f"| {error['error_type']} | {error['description']} | {error['resolution']} | "
                f"{error['components']} | `{error['example']}` | "
                f"{error['first_occurrence']} | {error['last_seen']} | {error['count']} |"
            )
            rows.append(row)

        content = (
            "# Error Issues Report\n\n"
            + table_header
            + table_separator
            + "\n".join(rows)
        )

    output_file.write_text(content, encoding="utf-8")
    logger.info("Wrote error report to %s", output_file)


def main() -> None:
    """Main entry point for standalone execution."""
    try:
        # Read log lines from stdin
        log_lines = [line.strip() for line in sys.stdin.readlines()]
        if not log_lines:
            logger.error("No input received via stdin")
            sys.exit(1)

        errors = classify_errors(log_lines)
        generate_issues_markdown(errors)

    except Exception as e:
        logger.exception("Critical error in deepinfra_client: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
