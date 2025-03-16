from pathlib import Path
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


@pytest.fixture
def mock_responses():
    return {
        "controversy_response": {
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
        },
        "agent_response": {
            "messages": [{"role": "assistant", "content": "Test analysis"}],
            "sources": [{"name": "Test Source", "url": "http://test.com"}],
        },
    }


@flow
async def test_analyze_companies_flow_inner(mock_responses, dokku_storage_path):
    test_csv_path = Path(__file__).parent / "test_companies.csv"
    output_path = dokku_storage_path / "data" / "test_output.json"

    with (
        patch(
            "flows.controversy_analysis.analyze_entity_controversies",
        ) as mock_controversy,
        patch("flows.agent_analysis.analyze_entity_with_agent") as mock_agent,
    ):

        # Configure mocks
        mock_controversy.return_value = mock_responses["controversy_response"]
        mock_agent.return_value = mock_responses["agent_response"]

        # Test with small batch size to verify concurrent processing
        results = await analyze_companies_flow(
            csv_path=str(test_csv_path),
            output_path=str(output_path),
            batch_size=2,  # Small batch size for testing
        )

        # Verify basic structure
        assert isinstance(results, list)
        assert len(results) > 0

        # Verify each result
        for result in results:
            assert isinstance(result, dict)
            assert all(
                key in result for key in ["name", "controversies", "agent_analysis"]
            )
            assert isinstance(result["controversies"], list)
            assert isinstance(result["agent_analysis"], dict)

            # Verify controversy data
            for controversy in result["controversies"]:
                assert "title" in controversy
                assert "description" in controversy
                assert "source" in controversy
                assert all(
                    key in controversy["source"]
                    for key in ["name", "url", "credibility"]
                )

            # Verify agent analysis
            assert "messages" in result["agent_analysis"]
            assert "sources" in result["agent_analysis"]
            assert len(result["agent_analysis"]["messages"]) > 0
            assert len(result["agent_analysis"]["sources"]) > 0

        # Verify concurrent processing
        assert mock_controversy.call_count > 0
        assert mock_agent.call_count > 0

        # Verify output file was created in Dokku storage
        assert output_path.exists()

        return results


@pytest.mark.asyncio
async def test_analyze_companies_flow(mock_responses, dokku_storage_path) -> None:
    result = await test_analyze_companies_flow_inner(mock_responses, dokku_storage_path)
    assert result is not None
    assert isinstance(result, list)

    # Test error handling
    with patch(
        "flows.controversy_analysis.analyze_entity_controversies",
    ) as mock_controversy:
        mock_controversy.side_effect = Exception("Test error")

        output_path = dokku_storage_path / "data" / "test_error_output.json"
        result = await analyze_companies_flow(
            csv_path=str(Path(__file__).parent / "test_companies.csv"),
            output_path=str(output_path),
        )

        # Verify error handling
        assert isinstance(result, list)
        error_results = [
            r for r in result if "error" in r.get("controversy_summary", "").lower()
        ]
        assert len(error_results) > 0

        # Verify error output was saved
        assert output_path.exists()
