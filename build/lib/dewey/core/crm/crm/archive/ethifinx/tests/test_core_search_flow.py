from unittest.mock import Mock, patch

import pytest

from ethifinx.research.search_flow import (
    APIClient,
    DataProcessor,
    DataStore,
    SearchFlow,
    call_deepseek_api,
    extract_structured_data,
    generate_search_queries,
    generate_summary,
    get_company_context,
    get_connection,
    get_incomplete_research,
    get_research_status,
    get_top_companies,
    is_investment_product,
)


@pytest.fixture
def mock_components():
    """Fixture to provide mock components."""
    data_store = Mock(spec=DataStore)
    data_store.save_to_db.return_value = None
    data_store.backup_to_s3.return_value = None
    data_store.save = Mock(return_value=True)

    return {
        "api_client": Mock(
            spec=APIClient, **{"fetch_data.return_value": {"data": "test"}}
        ),
        "data_processor": Mock(
            spec=DataProcessor, **{"process.return_value": {"processed": "test"}}
        ),
        "data_store": data_store,
    }


def test_search_flow_fetch_data_success(mock_components):
    """Test successful data fetching."""
    flow = SearchFlow(
        api_client=mock_components["api_client"],
        data_processor=mock_components["data_processor"],
        data_store=mock_components["data_store"],
    )

    result = flow.process_search("test_query")
    assert result["processed"] == "test"
    mock_components["api_client"].fetch_data.assert_called_once()
    mock_components["data_processor"].process.assert_called_once()
    mock_components["data_store"].save.assert_called_once()


def test_search_flow_fetch_data_failure(mock_components):
    """Test data fetching failure."""
    mock_components["api_client"].fetch_data.side_effect = Exception("API Error")

    flow = SearchFlow(
        api_client=mock_components["api_client"],
        data_processor=mock_components["data_processor"],
        data_store=mock_components["data_store"],
    )

    with pytest.raises(Exception):
        flow.process_search("test_query")


def test_search_flow_process_search_success(mock_components):
    """Test successful search flow."""
    flow = SearchFlow(
        api_client=mock_components["api_client"],
        data_processor=mock_components["data_processor"],
        data_store=mock_components["data_store"],
    )

    result = flow.process_search("test_query")
    assert result["processed"] == "test"
    mock_components["api_client"].fetch_data.assert_called_once()
    mock_components["data_processor"].process.assert_called_once()
    mock_components["data_store"].save.assert_called_once()


def test_search_flow_process_search_failure(mock_components):
    """Test search flow failure."""
    mock_components["api_client"].fetch_data.side_effect = Exception("API Error")

    flow = SearchFlow(
        api_client=mock_components["api_client"],
        data_processor=mock_components["data_processor"],
        data_store=mock_components["data_store"],
    )

    with pytest.raises(Exception):
        flow.process_search("test_query")
