
# Refactored from: test_agent_analysis
# Date: 2025-03-16T16:19:11.188691
# Refactor Version: 1.0
import os
from unittest.mock import AsyncMock, patch

import pytest
from flows.agent_analysis import (
    agent_search,
    analyze_entity_with_agent,
    extract_key_findings,
)
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


def validate_agent_output(result) -> None:
    assert isinstance(result, dict)
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) > 0
    assert "role" in result["messages"][0]
    assert "content" in result["messages"][0]
    assert "sources" in result
    assert isinstance(result["sources"], list)
    for source in result["sources"]:
        assert "name" in source
        assert "url" in source


@flow
async def test_agent_search_inner():
    mock_response = {
        "messages": [{"role": "assistant", "content": "Test search results"}],
        "sources": [{"name": "Test Source", "url": "http://test.com"}],
    }

    with patch("flows.agent_analysis.search_with_agent") as mock_search:
        mock_search.return_value = mock_response
        result = await agent_search("Test Company")
        validate_agent_output(result)
        return result


@pytest.mark.asyncio
async def test_agent_search() -> None:
    result = await test_agent_search_inner()
    assert result is not None


@flow
async def test_extract_key_findings_inner():
    mock_response = {
        "messages": [{"role": "assistant", "content": "Test findings"}],
        "sources": [{"name": "Test Source", "url": "http://test.com"}],
    }

    with patch("flows.agent_analysis.extract_findings") as mock_extract:
        mock_extract.return_value = mock_response
        result = await extract_key_findings("Test analysis")
        validate_agent_output(result)
        return result


@pytest.mark.asyncio
async def test_extract_key_findings() -> None:
    result = await test_extract_key_findings_inner()
    assert result is not None


@flow
async def test_analyze_entity_with_agent_inner():
    mock_response = {
        "messages": [{"role": "assistant", "content": "Test analysis"}],
        "sources": [{"name": "Test Source", "url": "http://test.com"}],
    }

    with (
        patch("flows.agent_analysis.search_with_agent") as mock_search,
        patch("flows.agent_analysis.extract_findings") as mock_extract,
    ):
        mock_search.return_value = mock_response
        mock_extract.return_value = mock_response
        result = await analyze_entity_with_agent("Test Company")
        validate_agent_output(result)
        return result


@pytest.mark.asyncio
async def test_analyze_entity_with_agent() -> None:
    result = await test_analyze_entity_with_agent_inner()
    assert result is not None


@flow
async def test_analyze_entity_with_agent_error_inner():
    with patch("flows.agent_analysis.search_with_agent") as mock_search:
        mock_search.side_effect = Exception("Test error")
        result = await analyze_entity_with_agent("Test Company")
        assert result == {"error": "Failed to analyze entity: Test error"}
        return result


@pytest.mark.asyncio
async def test_analyze_entity_with_agent_error() -> None:
    result = await test_analyze_entity_with_agent_error_inner()
    assert result is not None


@flow
async def test_analyze_entity_with_agent_companies_inner(companies_data) -> bool:
    mock_responses = {
        "Farmer Mac": {
            "messages": [{"role": "assistant", "content": "Farmer Mac analysis"}],
            "sources": [{"name": "Test Source", "url": "http://test.com"}],
        },
        "Crocs": {
            "messages": [{"role": "assistant", "content": "Crocs analysis"}],
            "sources": [{"name": "Test Source", "url": "http://test.com"}],
        },
        "Mercadolibre": {
            "messages": [{"role": "assistant", "content": "Mercadolibre analysis"}],
            "sources": [{"name": "Test Source", "url": "http://test.com"}],
        },
    }

    with (
        patch("flows.agent_analysis.search_with_agent") as mock_search,
        patch("flows.agent_analysis.extract_findings") as mock_extract,
    ):
        for company in companies_data:
            mock_search.return_value = mock_responses[company]
            mock_extract.return_value = mock_responses[company]
            result = await analyze_entity_with_agent(company)
            validate_agent_output(result)
            assert result == mock_responses[company]
        return True


@pytest.mark.asyncio
async def test_analyze_entity_with_agent_companies(companies_data) -> None:
    result = await test_analyze_entity_with_agent_companies_inner(companies_data)
    assert result is True
