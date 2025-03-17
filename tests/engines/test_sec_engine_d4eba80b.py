# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Tests for SEC EDGAR API Engine.
=========================
"""

from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from ethifinx.research.engines.sec import SECEngine


@pytest.fixture
async def engine():
    """Create a SECEngine instance for testing."""
    async with SECEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization() -> None:
    """Test that the engine initializes correctly."""
    engine = SECEngine(max_retries=2)
    assert isinstance(engine, SECEngine)
    assert engine.max_retries == 2


@pytest.mark.asyncio
async def test_process_method(engine) -> None:
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "SEC engine ready"


@pytest.mark.asyncio
async def test_get_company_tickers(engine) -> None:
    """Test company tickers retrieval."""
    mock_response = {
        "0": {"cik_str": "0000320193", "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": "0000789019", "ticker": "MSFT", "title": "Microsoft Corp"},
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_company_tickers()

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_company_facts(engine) -> None:
    """Test company facts retrieval."""
    mock_response = {
        "cik": "0000320193",
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Assets": {
                    "label": "Assets",
                    "description": "Sum of the carrying amounts...",
                    "units": {
                        "USD": [
                            {
                                "end": "2023-09-30",
                                "val": 352583000000,
                                "accn": "0000320193-23-000077",
                                "fy": 2023,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2023-10-27",
                            },
                        ],
                    },
                },
            },
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_company_facts("320193")

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_company_concept(engine) -> None:
    """Test company concept retrieval."""
    mock_response = {
        "cik": "0000320193",
        "taxonomy": "us-gaap",
        "tag": "Assets",
        "label": "Assets",
        "description": "Sum of the carrying amounts...",
        "units": {
            "USD": [
                {
                    "end": "2023-09-30",
                    "val": 352583000000,
                    "accn": "0000320193-23-000077",
                    "fy": 2023,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2023-10-27",
                },
            ],
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_company_concept("320193", "us-gaap", "Assets")

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_submissions(engine) -> None:
    """Test submissions retrieval."""
    mock_response = {
        "cik": "0000320193",
        "entityType": "operating",
        "sic": "3571",
        "sicDescription": "Electronic Computers",
        "insiderTransactionForOwnerExists": 1,
        "insiderTransactionForIssuerExists": 1,
        "name": "Apple Inc.",
        "tickers": ["AAPL"],
        "exchanges": ["Nasdaq"],
        "ein": "942404110",
        "description": "Apple Inc. designs, manufactures...",
        "website": "www.apple.com",
        "category": "Large accelerated filer",
        "fiscalYearEnd": "0930",
        "stateOfIncorporation": "CA",
        "stateOfIncorporationDescription": "CA",
        "addresses": {},
        "phone": "408-996-1010",
        "flags": "Large accelerated filer",
        "formerNames": [],
        "filings": {},
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_submissions("320193")

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_company_filings(engine) -> None:
    """Test company filings retrieval."""
    mock_response = {
        "cik": "0000320193",
        "entityType": "operating",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-23-000077"],
                "filingDate": ["2023-10-27"],
                "reportDate": ["2023-09-30"],
                "form": ["10-K"],
                "primaryDocument": ["d10k.htm"],
                "primaryDocDescription": ["Form 10-K"],
                "fileNumber": ["001-36743"],
                "filmNumber": ["231264451"],
                "items": ["1.01,2.02,9.01"],
                "size": [1234567],
                "isXBRL": [1],
                "isInlineXBRL": [1],
                "primaryDocumentUrl": ["..."],
                "filingUrl": ["..."],
            },
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_company_filings(
            "320193",
            form_type="10-K",
            start_date="2023-01-01",
            end_date="2023-12-31",
        )

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_mutual_fund_search(engine) -> None:
    """Test mutual fund search."""
    mock_response = {
        "results": [
            {
                "seriesId": "S000001234",
                "name": "Example Fund",
                "ticker": "EXFND",
                "cik": "0001234567",
                "classCount": 3,
                "lastUpdated": "2023-12-31",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_mutual_fund_search(ticker="EXFND")

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_mutual_fund_series(engine) -> None:
    """Test mutual fund series retrieval."""
    mock_response = {
        "seriesId": "S000001234",
        "name": "Example Fund",
        "classCount": 3,
        "lastUpdated": "2023-12-31",
        "classes": [{"classId": "C000001234", "name": "Class A", "ticker": "EXFND"}],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_mutual_fund_series("S000001234")

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_company_financial_statements(engine) -> None:
    """Test financial statements retrieval."""
    mock_response = {
        "cik": "0000320193",
        "taxonomy": "us-gaap",
        "statements": {
            "BalanceSheet": {
                "Assets": 352583000000,
                "Liabilities": 278532000000,
                "StockholdersEquity": 74051000000,
            },
            "IncomeStatement": {"Revenue": 383285000000, "NetIncome": 96995000000},
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_company_financial_statements(
            "320193",
            form_type="10-K",
            filing_date="2023-10-27",
        )

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_search_retry_on_error(engine) -> None:
    """Test search retries on API errors."""
    mock_response = {"cik": "0000320193"}

    with patch("aiohttp.ClientSession.get") as mock_get:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()

        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response

        mock_get.side_effect = [mock_error_context, mock_success_context]

        result = await engine.get_company_facts("320193")

        assert result == mock_response
        assert mock_get.call_count == 2
