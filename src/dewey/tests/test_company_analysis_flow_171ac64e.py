import os
from unittest.mock import AsyncMock, patch

import pytest
from flows.company_analysis_flow import analyze_companies_flow
from prefect import flow


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock_client:
        client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = client
        mock_client.return_value.__aexit__.return_value = None
        yield client


@flow
async def test_analyze_companies_flow_inner() -> None:
    # Create test data
    test_csv_path = os.path.join(os.path.dirname(__file__), "test_companies.csv")

    mock_controversy_response = {
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

    mock_agent_response = {
        "messages": [{"role": "assistant", "content": "Test analysis"}],
        "sources": [{"name": "Test Source", "url": "http://test.com"}],
    }

    with (
        patch(
            "flows.controversy_analysis.analyze_entity_controversies",
        ) as mock_controversy,
        patch("flows.agent_analysis.analyze_entity_with_agent") as mock_agent,
    ):

        mock_controversy.return_value = mock_controversy_response
        mock_agent.return_value = mock_agent_response

        results = await analyze_companies_flow(
            csv_path=test_csv_path,
            output_path="test_output.json",
        )

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert "name" in result
            assert "controversies" in result
            assert "agent_analysis" in result
            assert isinstance(result["controversies"], list)
            assert isinstance(result["agent_analysis"], dict)


@pytest.mark.asyncio
async def test_analyze_companies_flow() -> None:
    await test_analyze_companies_flow_inner()
