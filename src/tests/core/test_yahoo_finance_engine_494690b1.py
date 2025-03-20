# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Tests for Yahoo Finance Research Engine.
====================================
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from ethifinx.research.engines.yahoo_finance import YahooFinanceEngine


@pytest.fixture
def engine():
    """Create a YahooFinanceEngine instance for testing."""
    return YahooFinanceEngine(max_retries=2)


def test_engine_initialization(engine) -> None:
    """Test that the engine initializes correctly."""
    assert isinstance(engine, YahooFinanceEngine)
    assert engine.max_retries == 2


@pytest.mark.asyncio
async def test_process_method(engine) -> None:
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "YahooFinance engine ready"


def test_fetch_history_valid_ticker(engine) -> None:
    """Test fetching history for a valid ticker."""
    df = engine.fetch_history(
        "AAPL",
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "ticker" in df.columns
    assert "date" in df.columns
    assert "open" in df.columns
    assert "close" in df.columns
    assert "volume" in df.columns
    assert "data_source" in df.columns
    assert "last_updated_at" in df.columns

    # Check data quality
    assert df["ticker"].unique() == ["AAPL"]
    assert df["data_source"].unique() == ["yahoo"]
    assert pd.to_datetime(df["date"]).is_monotonic_increasing


def test_fetch_history_invalid_ticker(engine) -> None:
    """Test fetching history for an invalid ticker."""
    df = engine.fetch_history("INVALID_TICKER_123")
    assert df is None


def test_fetch_batch(engine) -> None:
    """Test batch fetching for multiple tickers."""
    tickers = ["AAPL", "MSFT", "INVALID_TICKER_123"]
    results = engine.fetch_batch(
        tickers,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )

    assert isinstance(results, dict)
    assert len(results) == len(tickers)

    # Valid tickers should have data
    assert isinstance(results["AAPL"], pd.DataFrame)
    assert isinstance(results["MSFT"], pd.DataFrame)

    # Invalid ticker should be None
    assert results["INVALID_TICKER_123"] is None


def test_process_dataframe(engine) -> None:
    """Test dataframe processing with sample data."""
    # Create sample data
    sample_data = {
        "Date": [datetime.now() - timedelta(days=i) for i in range(5)],
        "Open": [100 + i for i in range(5)],
        "High": [101 + i for i in range(5)],
        "Low": [99 + i for i in range(5)],
        "Close": [100.5 + i for i in range(5)],
        "Volume": [1000000 + i for i in range(5)],
    }
    df = pd.DataFrame(sample_data)
    df = df.set_index("Date")

    # Process the dataframe
    processed_df = engine._process_dataframe(df, "TEST")

    # Verify processing
    assert "date" in processed_df.columns
    assert "ticker" in processed_df.columns
    assert processed_df["ticker"].unique() == ["TEST"]
    assert processed_df["data_source"].unique() == ["yahoo"]
    assert len(processed_df) == 5
