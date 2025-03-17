import pytest
from pathlib import Path
import json
from datetime import datetime
from ethifinx.research.workflows.output_handler import ResearchOutputHandler
import tempfile
import shutil


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def output_handler(temp_output_dir):
    """Create a ResearchOutputHandler instance with a temporary output directory."""
    return ResearchOutputHandler(output_dir=temp_output_dir)


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "Company": "Test Corp",
        "Symbol": "TEST",
        "Category": "Technology",
        "Criteria": "ESG",
    }


@pytest.fixture
def sample_results():
    """Sample analysis results for testing."""
    return {
        "query": "Test Corp Technology ESG ethical controversies violations",
        "results": [
            {
                "title": "Test Result",
                "link": "http://example.com",
                "snippet": "Test snippet",
                "source": "Test source",
            }
        ],
        "analysis": {"content": "Test analysis content"},
    }


def test_init_creates_output_dir(temp_output_dir):
    """Test that initialization creates the output directory."""
    handler = ResearchOutputHandler(output_dir=temp_output_dir)
    assert Path(temp_output_dir).exists()
    assert Path(temp_output_dir).is_dir()


def test_generate_metadata(output_handler):
    """Test metadata generation."""
    metadata = output_handler.generate_metadata()
    assert isinstance(metadata, dict)
    assert "timestamp" in metadata
    assert metadata["version"] == "1.0"
    assert metadata["type"] == "ethical_analysis"
    # Verify timestamp is valid ISO format
    datetime.fromisoformat(metadata["timestamp"])


def test_format_company_analysis(output_handler, sample_company_data, sample_results):
    """Test company analysis formatting."""
    formatted = output_handler.format_company_analysis(
        sample_company_data, sample_results
    )

    assert formatted["company_name"] == "Test Corp"
    assert formatted["symbol"] == "TEST"
    assert formatted["primary_category"] == "Technology"
    assert formatted["current_criteria"] == "ESG"

    assert "historical" in formatted["analysis"]
    assert "evidence" in formatted["analysis"]
    assert "categorization" in formatted["analysis"]

    assert formatted["analysis"]["evidence"]["query"] == sample_results["query"]
    assert formatted["analysis"]["evidence"]["sources"] == sample_results["results"]

    assert isinstance(formatted["metadata"]["analysis_timestamp"], str)
    datetime.fromisoformat(formatted["metadata"]["analysis_timestamp"])


def test_save_research_output(output_handler, sample_company_data, sample_results):
    """Test saving research output to file."""
    results_by_company = {"Test Corp": sample_results}
    companies_data = [sample_company_data]

    output_path = output_handler.save_research_output(
        results_by_company=results_by_company,
        companies_data=companies_data,
        prefix="test_analysis",
    )

    assert output_path.exists()
    assert output_path.is_file()

    # Verify file content
    with open(output_path) as f:
        saved_data = json.load(f)

    assert "meta" in saved_data
    assert "companies" in saved_data
    assert len(saved_data["companies"]) == 1
    assert saved_data["companies"][0]["company_name"] == "Test Corp"


def test_save_research_output_empty(output_handler):
    """Test saving research output with empty data."""
    output_path = output_handler.save_research_output(
        results_by_company={}, companies_data=[], prefix="empty_analysis"
    )

    assert output_path.exists()
    with open(output_path) as f:
        saved_data = json.load(f)

    assert "meta" in saved_data
    assert "companies" in saved_data
    assert len(saved_data["companies"]) == 0


def test_handle_missing_company_data(output_handler, sample_results):
    """Test handling of missing company data fields."""
    incomplete_company = {"Company": "Incomplete Corp"}
    results_by_company = {"Incomplete Corp": sample_results}

    formatted = output_handler.format_company_analysis(
        incomplete_company, sample_results
    )

    assert formatted["company_name"] == "Incomplete Corp"
    assert formatted["symbol"] == ""
    assert formatted["primary_category"] == ""
    assert formatted["current_criteria"] == ""
