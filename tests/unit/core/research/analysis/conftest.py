"""Common test fixtures for analysis tests."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from dewey.core.db.connection import get_connection
from dewey.llm.llm_utils import LLMHandler

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    return mock_conn

@pytest.fixture
def mock_llm_handler():
    """Mock LLM handler."""
    mock_handler = MagicMock(spec=LLMHandler)
    mock_handler.generate_response.return_value = "Test analysis response"
    mock_handler.parse_json_response.return_value = {
        "analysis": "Test analysis",
        "summary": "Test summary",
        "ethical_score": 7.5,
        "risk_level": "medium"
    }
    return mock_handler

@pytest.fixture
def mock_search_results():
    """Mock search results."""
    return [
        {
            "title": "Test Result",
            "link": "http://test.com",
            "snippet": "Test snippet",
            "source": "test.com"
        }
    ]

@pytest.fixture
def sample_companies_csv(tmp_data_dir):
    """Create a sample companies.csv file."""
    companies_data = """Company,Symbol,Category,Criteria
Test Corp,TEST,Test Category,Test Criteria
Another Corp,ANTR,Another Category,Another Criteria"""
    
    csv_path = tmp_data_dir / "companies.csv"
    csv_path.write_text(companies_data)
    return csv_path

@pytest.fixture
def mock_output_handler():
    """Mock output handler."""
    mock_handler = MagicMock()
    mock_handler.save_results.return_value = None
    return mock_handler 