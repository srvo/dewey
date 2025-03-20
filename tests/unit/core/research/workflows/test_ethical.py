import json
from unittest.mock import MagicMock, ANY

import pytest

from dewey.core.research.workflows.ethical import EthicalAnalysisWorkflow
from dewey.core.research.engines import BaseEngine
from dewey.core.research.output import ResearchOutputHandler


@pytest.fixture
def mock_search_engine():
    """Function mock_search_engine."""
    engine = MagicMock(spec=BaseEngine)
    engine.search.side_effect = [
        # Results for Company A
        [
            {
                "title": "Test Result 1",
                "source": "example.com",
                "snippet": "Company A has good ethical practices",
            },
            {
                "title": "Test Result 2",
                "source": "example.org",
                "snippet": "Company A faces some challenges",
            },
        ],
        # Results for Company B
        [
            {
                "title": "Test Result 3",
                "source": "example.net",
                "snippet": "Company B sustainability report",
            },
        ],
    ]
    return engine


@pytest.fixture
def mock_analysis_engine():
    """Function mock_analysis_engine."""
    engine = MagicMock(spec=BaseEngine)
    engine.analyze.side_effect = [
        # Results for Company A
        "Ethical analysis result for Company A",
        "Risk assessment result for Company A",
        # Results for Company B
        "Ethical analysis result for Company B",
        "Risk assessment result for Company B",
    ]
    return engine


@pytest.fixture
def mock_output_handler():
    """Function mock_output_handler."""
    return MagicMock(spec=ResearchOutputHandler)


@pytest.fixture
def workflow(tmp_path, mock_search_engine, mock_analysis_engine, mock_output_handler):
    """Function workflow."""
    return EthicalAnalysisWorkflow(
        data_dir=str(tmp_path),
        search_engine=mock_search_engine,
        analysis_engine=mock_analysis_engine,
        output_handler=mock_output_handler,
    )


def test_init_default():
    """Test initialization with default parameters."""
    workflow = EthicalAnalysisWorkflow()
    assert isinstance(workflow.search_engine, BaseEngine)
    assert isinstance(workflow.analysis_engine, BaseEngine)
    assert isinstance(workflow.output_handler, ResearchOutputHandler)
    assert workflow.data_dir == "data"


def test_build_query():
    """Test query building."""
    workflow = EthicalAnalysisWorkflow()
    query = workflow.build_query("Company A", "Technology")
    assert "Company A" in query
    assert "Technology" in query
    assert "ethics" in query
    assert "controversy" in query
    assert "sustainability" in query
    assert "corporate responsibility" in query


def test_word_count():
    """Test word counting."""
    workflow = EthicalAnalysisWorkflow()
    assert workflow.word_count("one two three") == 3
    assert workflow.word_count("") == 0
    assert workflow.word_count("single") == 1


def test_analyze_company_profile(workflow):
    """Test company profile analysis."""
    search_results = [
        {
            "title": "Test Result",
            "source": "example.com",
            "snippet": "Company info",
        }
    ]

    result = workflow.analyze_company_profile("Company A", search_results)

    assert "ethical_analysis" in result
    assert "risk_assessment" in result
    assert workflow.stats["total_analyses"] == 1
    assert workflow.stats["total_analysis_words"] > 0

    workflow.analysis_engine.analyze.assert_any_call(
        "ethical_analysis",
        company_name="Company A",
        search_results=ANY,
    )
    workflow.analysis_engine.analyze.assert_any_call(
        "risk_assessment",
        company_name="Company A",
        search_results=ANY,
    )


def test_analyze_company_profile_no_results(workflow):
    """Test company profile analysis with no search results."""
    result = workflow.analyze_company_profile("Company A", [])

    assert result["ethical_analysis"] == "No search results available for analysis"
    assert result["risk_assessment"] == "Unable to assess risks due to lack of data"
    assert workflow.stats["total_analyses"] == 0


def test_execute(workflow, tmp_path):
    """Test workflow execution."""
    # Create test companies.csv
    companies_file = tmp_path / "companies.csv"
    companies_data = "name,category\nCompany A,Technology\nCompany B,Finance"
    companies_file.write_text(companies_data)

    result = workflow.execute()

    assert len(result["results"]) == 2
    assert result["stats"]["companies_processed"] == 2
    assert result["stats"]["total_searches"] == 2
    assert result["stats"]["total_results"] > 0

    workflow.output_handler.save_results.assert_called()


def test_execute_missing_companies_file(workflow):
    """Test workflow execution with missing companies file."""
    with pytest.raises(FileNotFoundError):
        workflow.execute()


def test_execute_error_handling(workflow, tmp_path):
    """Test error handling during execution."""
    # Create test companies.csv
    companies_file = tmp_path / "companies.csv"
    companies_data = "name,category\nCompany A,Technology"
    companies_file.write_text(companies_data)

    # Make search engine raise an exception
    workflow.search_engine.search.side_effect = Exception("Search failed")

    result = workflow.execute()

    assert len(result["results"]) == 0
    assert result["stats"]["companies_processed"] == 0
    assert result["stats"]["total_searches"] == 0
