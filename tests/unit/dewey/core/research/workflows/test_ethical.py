#!/usr/bin/env python3
"""Unit tests for the ethical analysis workflow."""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.core.research.engines import BaseEngine
from dewey.core.research.workflows.ethical import EthicalAnalysisWorkflow
from dewey.llm.llm_utils import get_llm_client
from tests.dewey.core.research.analysis.test_workflow_integration import ResearchOutputHandler


@pytest.fixture
def mock_base_script(tmp_path: Path) -> MagicMock:
    """Fixture to create a mock BaseScript instance."""
    mock = MagicMock(spec=BaseScript)
    mock.config = {
        "paths": {"data_dir": str(tmp_path)},
        "logging": {"level": "INFO", "format": "%(message)s"},
    }
    mock.logger = logging.getLogger(__name__)
    mock.logger.setLevel(logging.INFO)
    return mock


@pytest.fixture
def mock_search_engine() -> MagicMock:
    """Fixture to create a mock search engine."""
    mock = MagicMock(spec=BaseEngine)
    mock.search.return_value = [
        {"title": "Test Result 1", "link": "http://example.com/1", "snippet": "Test snippet 1", "source": "Example Source"},
        {"title": "Test Result 2", "link": "http://example.com/2", "snippet": "Test snippet 2", "source": "Example Source"},
    ]
    return mock


@pytest.fixture
def mock_analysis_engine() -> MagicMock:
    """Fixture to create a mock analysis engine."""
    mock = MagicMock(spec=BaseEngine)
    mock.add_template.return_value = None
    return mock


@pytest.fixture
def mock_output_handler(tmp_path: Path) -> MagicMock:
    """Fixture to create a mock output handler."""
    mock = MagicMock(spec=ResearchOutputHandler)
    mock.save_results.return_value = None
    return mock


@pytest.fixture
def ethical_analysis_workflow(
    tmp_path: Path, mock_search_engine: MagicMock, mock_analysis_engine: MagicMock, mock_output_handler: MagicMock
) -> EthicalAnalysisWorkflow:
    """Fixture to create an EthicalAnalysisWorkflow instance with mocks."""
    workflow = EthicalAnalysisWorkflow(
        data_dir=str(tmp_path),
        search_engine=mock_search_engine,
        analysis_engine=mock_analysis_engine,
        output_handler=mock_output_handler,
    )
    workflow.llm = MagicMock()
    workflow.llm.generate_response.return_value = "Test analysis"
    return workflow


def test_ethical_analysis_workflow_initialization(ethical_analysis_workflow: EthicalAnalysisWorkflow, tmp_path: Path) -> None:
    """Test the initialization of the EthicalAnalysisWorkflow."""
    assert ethical_analysis_workflow.data_dir == Path(tmp_path)
    assert ethical_analysis_workflow.search_engine is not None
    assert ethical_analysis_workflow.analysis_engine is not None
    assert ethical_analysis_workflow.output_handler is not None
    assert ethical_analysis_workflow.name == "EthicalAnalysisWorkflow"
    assert ethical_analysis_workflow.description == "Workflow for analyzing companies from an ethical perspective."
    assert ethical_analysis_workflow.config_section == "ethical_analysis"
    assert ethical_analysis_workflow.requires_db is True
    assert ethical_analysis_workflow.enable_llm is True
    assert ethical_analysis_workflow.stats == {
        "companies_processed": 0,
        "total_searches": 0,
        "total_results": 0,
        "total_snippet_words": 0,
        "total_analyses": 0,
        "total_analysis_words": 0,
    }


def test_build_query(ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
    """Test the build_query method."""
    company_data = {"Company": "Test Company"}
    query = ethical_analysis_workflow.build_query(company_data)
    assert "Test Company" in query
    assert "ethical" in query
    assert "ethics" in query


@pytest.mark.parametrize(
    "text, expected_count",
    [
        ("This is a test", 4),
        ("", 0),
        ("  leading and trailing spaces  ", 5),
    ],
)
def test_word_count(ethical_analysis_workflow: EthicalAnalysisWorkflow, text: str, expected_count: int) -> None:
    """Test the word_count method."""
    count = ethical_analysis_workflow.word_count(text)
    assert count == expected_count


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_setup_database(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
    """Test the setup_database method."""
    mock_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_conn
    ethical_analysis_workflow.setup_database()
    assert mock_conn.execute.call_count == 6  # 3 create sequences + 3 create tables


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_analyze_company_profile(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
    """Test the analyze_company_profile method."""
    company = "Test Company"
    mock_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = [1]  # Mock search_id

    analysis_result = ethical_analysis_workflow.analyze_company_profile(company)

    assert analysis_result is not None
    assert analysis_result["company"] == company
    assert len(analysis_result["search_results"]) == 2
    assert analysis_result["analysis"] == "Test analysis"

    assert mock_conn.execute.call_count == 3  # Insert search, insert results, insert analysis
    ethical_analysis_workflow.search_engine.search.assert_called_once_with(f"{company} ethical issues controversies")
    ethical_analysis_workflow.llm.generate_response.assert_called_once()


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_analyze_company_profile_no_search_results(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
    """Test analyze_company_profile when no search results are returned."""
    ethical_analysis_workflow.search_engine.search.return_value = []
    company = "Test Company"
    result = ethical_analysis_workflow.analyze_company_profile(company)
    assert result is None
    ethical_analysis_workflow.search_engine.search.assert_called_once_with(f"{company} ethical issues controversies")
    mock_get_connection.assert_not_called()  # Ensure DB is not accessed


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_analyze_company_profile_db_error(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
    """Test analyze_company_profile when a database error occurs."""
    ethical_analysis_workflow.search_engine.search.return_value = [
        {"title": "Test Result", "link": "http://example.com", "snippet": "Test snippet", "source": "Example Source"}
    ]
    mock_get_connection.side_effect = Exception("Database error")
    company = "Test Company"
    result = ethical_analysis_workflow.analyze_company_profile(company)
    assert result is None
    ethical_analysis_workflow.logger.error.assert_called()


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_execute(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow, tmp_path: Path) -> None:
    """Test the execute method."""
    # Create a dummy companies.csv file
    companies_file = tmp_path / "companies.csv"
    with open(companies_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Company"])
        writer.writeheader()
        writer.writerow({"Company": "Test Company 1"})
        writer.writerow({"Company": "Test Company 2"})

    # Mock database interactions
    mock_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = [1]  # Mock search_id

    # Execute the workflow
    result = ethical_analysis_workflow.execute(str(tmp_path))

    # Assertions
    assert result is not None
    assert result["stats"]["companies_processed"] == 2
    assert result["stats"]["total_searches"] == 2
    assert result["stats"]["total_results"] == 4  # 2 results per company
    assert result["stats"]["total_analyses"] == 2
    assert len(result["results"]) == 2
    ethical_analysis_workflow.output_handler.save_results.assert_called_once()


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_execute_company_processing_error(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow, tmp_path: Path) -> None:
    """Test the execute method when an error occurs during company processing."""
    # Create a dummy companies.csv file
    companies_file = tmp_path / "companies.csv"
    with open(companies_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Company"])
        writer.writeheader()
        writer.writerow({"Company": "Test Company 1"})
        writer.writerow({"Company": "Test Company 2"})

    # Mock database interactions to raise an exception for the first company
    mock_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.side_effect = [Exception("Simulated DB error"), MagicMock()]  # First company raises exception

    # Execute the workflow
    result = ethical_analysis_workflow.execute(str(tmp_path))

    # Assertions
    assert result is not None
    assert result["stats"]["companies_processed"] == 2  # Both companies are processed (even with error)
    assert result["stats"]["total_searches"] == 1  # Only one successful search
    assert result["stats"]["total_results"] == 2  # Only results from one company
    assert result["stats"]["total_analyses"] == 1  # Only one successful analysis
    assert len(result["results"]) == 1  # Only one company's data is saved
    ethical_analysis_workflow.output_handler.save_results.assert_called_once()
    ethical_analysis_workflow.logger.error.assert_called()  # Error should be logged


@patch("dewey.core.research.workflows.ethical.get_connection")
def test_execute_file_not_found(mock_get_connection: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow, tmp_path: Path) -> None:
    """Test the execute method when the companies file is not found."""
    with pytest.raises(FileNotFoundError):
        ethical_analysis_workflow.execute(str(tmp_path))
    ethical_analysis_workflow.logger.error.assert_called()
    mock_get_connection.assert_not_called()


@patch("dewey.core.research.workflows.ethical.EthicalAnalysisWorkflow.execute")
def test_run(mock_execute: MagicMock, ethical_analysis_workflow: EthicalAnalysisWorkflow, tmp_path: Path) -> None:
    """Test the run method."""
    # Mock the get_config_value method to return a dummy data directory
    ethical_analysis_workflow.get_config_value = MagicMock(return_value=str(tmp_path))

    # Create a dummy companies.csv file
    companies_file = tmp_path / "companies.csv"
    companies_file.write_text("Company\nTest Company")

    # Call the run method
    ethical_analysis_workflow.run()

    # Assert that the execute method was called with the correct data directory
    mock_execute.assert_called_once_with(str(tmp_path))


def test_run_file_not_found(ethical_analysis_workflow: EthicalAnalysisWorkflow, tmp_path: Path) -> None:
    """Test the run method when the companies file is not found."""
    # Mock the get_config_value method to return a dummy data directory
    ethical_analysis_workflow.get_config_value = MagicMock(return_value=str(tmp_path))

    # Call the run method and assert that it raises a FileNotFoundError
    with pytest.raises(FileNotFoundError):
        ethical_analysis_workflow.run()

    # Assert that the logger's error method was called
    ethical_analysis_workflow.logger.error.assert_called()
