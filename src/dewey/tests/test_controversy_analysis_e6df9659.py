import os
from unittest.mock import AsyncMock, patch

import pytest
from flows.controversy_analysis import analyze_entity_controversies
from prefect import flow


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock_client:
        client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = client
        mock_client.return_value.__aexit__.return_value = None
        yield client


@pytest.fixture
def companies_data():
    with open(os.path.join(os.path.dirname(__file__), "test_companies.csv")) as f:
        return [line.strip().split(",")[0] for line in f.readlines()[1:]]


def validate_controversy_output(result) -> None:
    assert isinstance(result, dict)
    assert "controversies" in result
    assert isinstance(result["controversies"], list)

    for controversy in result["controversies"]:
        assert "title" in controversy
        assert "description" in controversy
        assert "source" in controversy
        assert isinstance(controversy["source"], dict)
        assert "name" in controversy["source"]
        assert "url" in controversy["source"]
        assert "credibility" in controversy["source"]
        assert "last_updated" in controversy["source"]


@flow
async def test_analyze_entity_controversies_inner():
    mock_response = {
        "controversies": [
            {
                "title": "Test Controversy",
                "description": "Test description",
                "source": {
                    "name": "Test Source",
                    "url": "http://test.com",
                    "credibility": "high",
                    "last_updated": "2024-01-01",
                },
            },
        ],
    }

    with patch("flows.controversy_analysis.search_controversies") as mock_search:
        mock_search.return_value = mock_response
        result = await analyze_entity_controversies("Test Company")
        validate_controversy_output(result)
        return result


@pytest.mark.asyncio
async def test_analyze_entity_controversies() -> None:
    await test_analyze_entity_controversies_inner()


@flow
async def test_analyze_entity_controversies_with_error_inner():
    with patch("flows.controversy_analysis.search_controversies") as mock_search:
        mock_search.side_effect = Exception("Test error")
        result = await analyze_entity_controversies("Test Company")
        assert result == {
            "controversies": [],
            "error": "Failed to analyze controversies: Test error",
        }
        return result


@pytest.mark.asyncio
async def test_analyze_entity_controversies_with_error() -> None:
    await test_analyze_entity_controversies_with_error_inner()


@flow
async def test_analyze_entity_controversies_with_companies_inner(
    companies_data,
) -> None:
    mock_responses = {
        "Farmer Mac": {
            "controversies": [
                {
                    "title": "Farmer Mac Controversy",
                    "description": "Test description",
                    "source": {
                        "name": "Test Source",
                        "url": "http://test.com",
                        "credibility": "high",
                        "last_updated": "2024-01-01",
                    },
                },
            ],
        },
        "Crocs": {
            "controversies": [
                {
                    "title": "Crocs Controversy",
                    "description": "Test description",
                    "source": {
                        "name": "Test Source",
                        "url": "http://test.com",
                        "credibility": "high",
                        "last_updated": "2024-01-01",
                    },
                },
            ],
        },
        "Mercadolibre": {
            "controversies": [
                {
                    "title": "Mercadolibre Controversy",
                    "description": "Test description",
                    "source": {
                        "name": "Test Source",
                        "url": "http://test.com",
                        "credibility": "high",
                        "last_updated": "2024-01-01",
                    },
                },
            ],
        },
    }

    with patch("flows.controversy_analysis.search_controversies") as mock_search:
        for company in companies_data:
            mock_search.return_value = mock_responses[company]
            result = await analyze_entity_controversies(company)
            validate_controversy_output(result)
            assert result == mock_responses[company]


@pytest.mark.asyncio
async def test_analyze_entity_controversies_with_companies(companies_data) -> None:
    await test_analyze_entity_controversies_with_companies_inner(companies_data)
