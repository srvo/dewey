```python
#!/usr/bin/env python3

"""Data import CLI commands."""

import csv
from pathlib import Path
from typing import Optional

import click
from sqlalchemy.orm import Session

from ethifinx.core.config import Config
from ethifinx.core.logging_config import setup_logging
from ethifinx.db.data_store import DataStore, get_connection, init_db
from ethifinx.db.models import Base

logger = setup_logging(__name__)


@click.group()
def cli() -> None:
    """Import data from various sources."""
    pass


def _ensure_db_initialized() -> None:
    """Ensure database is initialized with all tables."""
    # Don't reinitialize if already initialized (which happens in test setup)
    if not hasattr(_ensure_db_initialized, "_initialized"):
        init_db()
        engine = get_connection().__enter__().get_bind()
        Base.metadata.create_all(engine)
        _ensure_db_initialized._initialized = True


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def import_universe(file_path: str) -> None:
    """Import universe data from a CSV file.

    Args:
        file_path: Path to the CSV file.
    """
    try:
        _ensure_db_initialized()  # Initialize DB and create tables
        with get_connection() as session:
            data_store = DataStore(session=session)
            data_store.import_csv(file_path, "universe")
            click.echo("Successfully imported universe")
    except Exception as e:
        logger.error(f"Universe import failed: {e}")
        click.echo(f"Error: {str(e)}")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def import_portfolio(file_path: str) -> None:
    """Import portfolio data from a CSV file.

    Args:
        file_path: Path to the CSV file.
    """
    try:
        _ensure_db_initialized()  # Initialize DB and create tables
        with get_connection() as session:
            data_store = DataStore(session=session)
            data_store.import_csv(file_path, "portfolio")
            click.echo("Successfully imported portfolio")
    except Exception as e:
        logger.error(f"Portfolio import failed: {e}")
        click.echo(f"Error: {str(e)}")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--format", type=click.Choice(["csv", "json", "excel"]), default="csv")
def import_data(file_path: str, format: str) -> None:
    """Import data from a file.

    Args:
        file_path: Path to the data file.
        format: Format of the data file (csv, json, or excel).
    """
    try:
        data_store = DataStore()
        file_path = Path(file_path)

        logger.info(f"Importing data from {file_path}")
        if format == "csv":
            data_store.import_csv(file_path)
        elif format == "json":
            data_store.import_json(file_path)
        elif format == "excel":
            data_store.import_excel(file_path)

        logger.info("Data import completed successfully")
        click.echo("Data imported successfully.")
    except Exception as e:
        logger.error(f"Data import failed: {e}")
        click.echo(f"Error: {str(e)}", err=True)


if __name__ == "__main__":
    cli()
```
