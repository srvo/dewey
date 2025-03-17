"""Test CLI functionality."""

import csv
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine

from ethifinx.cli.importer import import_portfolio, import_universe
from ethifinx.db.data_store import get_connection, init_db
from ethifinx.db.models import Base  # Import Base to create tables


@pytest.fixture(scope="session")
def test_db(tmp_path_factory):
    """Create test database and tables."""
    # Create a temporary directory that persists for the session
    tmp_dir = tmp_path_factory.mktemp("db")
    db_path = tmp_dir / "test.db"
    db_url = f"sqlite:///{db_path}"

    # Initialize the database with this URL
    init_db(database_url=db_url)
    engine = get_connection().__enter__().get_bind()
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def runner(test_db):  # test_db dependency ensures tables are created
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_csv(tmp_path):
    """Create sample CSV files for different imports."""
    # Create universe CSV
    universe_csv = tmp_path / "universe.csv"
    universe_data = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "sector": "Technology",
            "market_cap": "2000000000",
        },
        {
            "ticker": "MSFT",
            "name": "Microsoft Corp",
            "sector": "Technology",
            "market_cap": "1800000000",
        },
    ]

    with open(universe_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["ticker", "name", "sector", "market_cap"]
        )
        writer.writeheader()
        writer.writerows(universe_data)

    # Create portfolio CSV
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_data = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "sector": "Technology",
            "weight": "0.25",
        },
        {
            "ticker": "MSFT",
            "name": "Microsoft Corp",
            "sector": "Technology",
            "weight": "0.25",
        },
    ]

    with open(portfolio_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "name", "sector", "weight"])
        writer.writeheader()
        writer.writerows(portfolio_data)

    return {"universe": universe_csv, "portfolio": portfolio_csv}


def test_universe_import(runner, sample_csv, test_db):
    """Test universe import command."""
    result = runner.invoke(import_universe, [str(sample_csv["universe"])])
    assert result.exit_code == 0
    assert "Successfully imported universe" in result.output


def test_portfolio_import(runner, sample_csv, test_db):
    """Test portfolio import command."""
    result = runner.invoke(import_portfolio, [str(sample_csv["portfolio"])])
    assert result.exit_code == 0
    assert "Successfully imported portfolio" in result.output
