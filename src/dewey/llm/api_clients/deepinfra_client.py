#!/usr/bin/env python3
"""
DeepInfra API Client (Legacy).

Handles error classification requests through the DeepInfra API with
improved error handling, retries, and chunking for large files.
"""

import os
import time
from pathlib import Path
from typing import Any

import requests

from dewey.core.base_script import BaseScript

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
CHUNK_SIZE = 1000  # Lines per processing chunk
MAX_TOKENS = 2000  # Conservative token limit for API

# logger = get_logger(__name__) # Removed global logger instance


class DeepInfraClient(BaseScript):
    """DeepInfra API client for error classification."""

    def __init__(
        self, api_key: str | None = None, base_url: str = "https://api.deepinfra.com",
    ) -> None:
        """Initialize the DeepInfra client."""
        super().__init__(name="deepinfra_client")
        self.logger.debug("Deep Infra client initialized")

        self.api_key = api_key or os.getenv("DEEPINFRA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Deep Infra API key not provided or found in environment variables.",
            )
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def setup_argparse(self):
        """Set up command line arguments."""
        parser = super().setup_argparse()
        parser.add_argument("input_file", type=Path, help="Path to input log file")
        parser.add_argument(
            "--output-file",
            type=Path,
            default=Path("issues.md"),
            help="Path to output markdown file",
        )
        return parser

    def classify_errors(self, log_lines: list[str]) -> list[dict[str, Any]]:
        """Classify errors using DeepInfra API with chunking and retry logic."""
        chunks = [
            log_lines[i : i + CHUNK_SIZE] for i in range(0, len(log_lines), CHUNK_SIZE)
        ]
        all_errors = {}

        api_url = self.config["settings"]["deepinfra_api_url"]
        api_key = self.config["settings"]["deepinfra_api_key"]

        for idx, chunk in enumerate(chunks):
            self.logger.info(
                "Processing chunk %d/%d (%d lines)", idx + 1, len(chunks), len(chunk),
            )
            prompt = (
                "Analyze these log lines and identify error patterns:\n\n"
                + "\n".join(chunk)
            )

            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        api_url,
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": MAX_TOKENS,
                        },
                        timeout=30,
                    )
                    response.raise_for_status()
                    chunk_errors = self.parse_api_response(response.json())

                    # Merge errors by hash to avoid duplicates
                    for error in chunk_errors:
                        error_hash = hashlib.md5(error["pattern"].encode()).hexdigest()
                        if error_hash not in all_errors:
                            all_errors[error_hash] = error
                    break

                except (requests.RequestException, KeyError) as e:
                    if attempt == MAX_RETRIES - 1:
                        self.logger.error(
                            "Failed to process chunk after %d retries: %s",
                            MAX_RETRIES,
                            e,
                        )
                        continue
                    time.sleep(RETRY_DELAY * (attempt + 1))

        return list(all_errors.values())

    def parse_api_response(self, response_data: dict) -> list[dict[str, Any]]:
        """Parse API response to extract error patterns."""
        try:
            content = response_data["choices"][0]["message"]["content"]
            errors = []

            # Simple parsing assuming one error pattern per line
            for line in content.split("\n"):
                if line.strip():
                    errors.append(
                        {
                            "pattern": line.strip(),
                            "count": 1,  # Basic count for now
                            "severity": "unknown",  # Could be enhanced
                        },
                    )

            return errors

        except (KeyError, IndexError) as e:
            self.logger.error("Failed to parse API response: %s", e)
            return []

    def generate_issues_markdown(
        self, errors: list[dict[str, Any]], output_file: Path,
    ) -> None:
        """Generate markdown report of identified issues."""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open("w") as f:
            f.write("# Error Analysis Report\n\n")
            f.write("## Identified Error Patterns\n\n")

            for error in sorted(errors, key=lambda x: x.get("count", 0), reverse=True):
                f.write(f"### Pattern: {error['pattern']}\n")
                f.write(f"- Count: {error['count']}\n")
                f.write(f"- Severity: {error['severity']}\n\n")

        self.logger.info("Generated report at %s", output_file)

    def execute(self) -> None:
        """Run the error classification process."""
        if not self.args.input_file.exists():
            self.logger.error("Input file does not exist: %s", self.args.input_file)
            sys.exit(1)

        with self.args.input_file.open() as f:
            log_lines = f.readlines()

        self.logger.info("Processing %d log lines", len(log_lines))
        errors = self.classify_errors(log_lines)
        self.generate_issues_markdown(errors, self.args.output_file)

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()


if __name__ == "__main__":
    client = DeepInfraClient()
    client.initialize()
    client.run()
