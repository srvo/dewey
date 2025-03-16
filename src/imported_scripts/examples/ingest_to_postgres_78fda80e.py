import logging
import os
from typing import Any

import pathway as pw

logging.basicConfig(level=logging.INFO)


def extract_filename(metadata: dict[str, Any]) -> str:
    """Extracts the filename from the metadata dictionary.

    Args:
        metadata: A dictionary containing metadata about the file.

    Returns:
        The filename extracted from the metadata.

    """
    return os.path.basename(metadata.get("path", ""))


def build_postgres_connection_string() -> str:
    """Builds a PostgreSQL connection string from environment variables.

    Returns:
        A connection string for PostgreSQL.

    """
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'db.srvo.org')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'pathway')} "
        f"user={os.environ.get('POSTGRES_USER', 'postgres')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', '')}"
    )


def mask_password(connection_string: str) -> str:
    """Masks the password in the connection string for logging purposes.

    Args:
        connection_string: The original connection string.

    Returns:
        The connection string with the password replaced by '***'.

    """
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return connection_string.replace(password, "***")


def run_pipeline() -> None:
    """Runs the data pipeline with continuous monitoring."""
    try:
        logging.info("Starting pipeline with continuous monitoring...")

        # Read input files
        input_files = pw.io.fs.read(
            "/opt/pathway/transcripts",
            format="plaintext",
            with_metadata=True,
            mode="streaming",
        )

        # Debug the available columns
        logging.info(f"Available columns: {input_files.schema}")

        # Just extract filename and content
        processed = input_files.select(
            filename=pw.apply(extract_filename, pw.this._metadata),
            content=pw.this.data,
        )

        # Build connection string directly
        connection_string = build_postgres_connection_string()

        # Log connection string (with password masked)
        safe_conn = mask_password(connection_string)
        logging.info(f"Using connection string: {safe_conn}")

        # Write to postgres using positional arguments
        pw.io.postgres.write(processed, connection_string, "raw_transcripts")

        logging.info("Running pipeline...")
        pw.run()

    except Exception as e:
        logging.exception(f"Pipeline error: {e!s}")
        raise


if __name__ == "__main__":
    run_pipeline()
