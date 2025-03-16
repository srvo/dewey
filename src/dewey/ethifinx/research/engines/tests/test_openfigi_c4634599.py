# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Tests for OpenFIGI engine."""

import time
from unittest.mock import patch

import pytest
import responses
from ethifinx.research.engines.openfigi import OpenFIGIEngine


@pytest.fixture
def engine():
    """Create an OpenFIGI engine instance with test API key."""
    return OpenFIGIEngine(api_key="test_key")


@pytest.fixture
def test_companies():
    """Sample company data for testing."""
    return [
        {"ticker": "AAPL", "security_name": "Apple Inc.", "tick": 5, "entity_id": 1},
        {
            "ticker": "MSFT",
            "security_name": "Microsoft Corporation",
            "tick": 3,
            "entity_id": 2,
        },
    ]


@pytest.fixture
def mock_figi_response():
    """Sample OpenFIGI API response."""
    return [
        {
            "data": [
                {
                    "figi": "BBG000B9XRY4",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                    "exchCode": "US",
                    "name": "APPLE INC",
                    "compositeFIGI": "BBG000B9XRY4",
                    "securityDescription": "AAPL",
                },
            ],
        },
        {
            "data": [
                {
                    "figi": "BBG000BPH459",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                    "exchCode": "US",
                    "name": "MICROSOFT CORP",
                    "compositeFIGI": "BBG000BPH459",
                    "securityDescription": "MSFT",
                },
            ],
        },
    ]


@responses.activate
async def test_get_figi_data(engine, test_companies, mock_figi_response) -> None:
    """Test getting FIGI data for companies."""
    # Mock the OpenFIGI API response
    responses.add(
        responses.POST,
        "https://api.openfigi.com/v3/mapping",
        json=mock_figi_response,
        status=200,
    )

    results = await engine.get_figi_data(test_companies)

    assert len(results) == 2
    assert results[0]["ticker"] == "AAPL"
    assert results[0]["figi"] == "BBG000B9XRY4"
    assert results[0]["lookup_status"] == "success"
    assert results[1]["ticker"] == "MSFT"
    assert results[1]["figi"] == "BBG000BPH459"
    assert results[1]["lookup_status"] == "success"


@responses.activate
async def test_get_figi_data_error(engine, test_companies) -> None:
    """Test error handling in FIGI data retrieval."""
    # Mock an API error response
    responses.add(responses.POST, "https://api.openfigi.com/v3/mapping", status=500)

    results = await engine.get_figi_data(test_companies)

    assert len(results) == 2
    assert all(r["lookup_status"].startswith("error after") for r in results)
    assert all(r["figi"] is None for r in results)


@pytest.mark.parametrize(
    ("figi_data", "expected_exchange"),
    [
        (
            [
                {
                    "exchCode": "US",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                },
                {
                    "exchCode": "LN",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                },
            ],
            "US",
        ),
        (
            [
                {
                    "exchCode": "LN",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                },
                {"exchCode": "US", "securityType": "ADR", "marketSector": "Equity"},
            ],
            "US",
        ),
        (
            [
                {
                    "exchCode": "LN",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                },
                {
                    "exchCode": "FR",
                    "securityType": "Common Stock",
                    "marketSector": "Equity",
                },
            ],
            "LN",
        ),
    ],
)
def test_filter_primary_listing(engine, figi_data, expected_exchange) -> None:
    """Test filtering for primary listing with different scenarios."""
    result = engine.filter_primary_listing(figi_data)
    assert result["exchCode"] == expected_exchange


async def test_process_companies(engine, test_companies, mock_figi_response) -> None:
    """Test processing multiple companies in batches."""
    with patch.object(engine, "get_figi_data", return_value=mock_figi_response):
        results = await engine.process_companies(test_companies, batch_size=1)
        assert len(results) == 2


def test_respect_rate_limit(engine) -> None:
    """Test rate limiting functionality."""
    with patch("time.sleep") as mock_sleep:
        engine.last_request_time = time.time()
        engine.respect_rate_limit()
        mock_sleep.assert_called_once()
