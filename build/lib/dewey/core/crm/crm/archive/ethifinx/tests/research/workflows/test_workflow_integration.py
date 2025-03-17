import csv
import json
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Type

import pytest

from ethifinx.db.data_store import get_connection, init_db
from ethifinx.research.engines.base import BaseEngine
from ethifinx.research.workflow import Workflow
from ethifinx.research.workflows.output_handler import ResearchOutputHandler


class MockSearchEngine(BaseEngine):
    """Mock search engine for testing."""

    def __init__(self, mock_results: List[Dict] = None):
        self.mock_results = mock_results or [
            {
                "title": "Mock Result",
                "link": "http://example.com",
                "snippet": "Mock snippet",
                "source": "Mock source",
            }
        ]

    def search(self, query: str) -> List[Dict]:
        return self.mock_results

    def process(self, data: Dict) -> Dict:
        """Process the data according to BaseEngine requirements."""
        return {"processed": True, "data": data}


class MockAnalysisEngine(BaseEngine):
    """Mock analysis engine for testing."""

    def __init__(self, mock_analysis: Dict = None):
        self.mock_analysis = mock_analysis or {
            "content": "Mock analysis content",
            "summary": "Mock summary",
        }

    def analyze(self, data: List[Dict]) -> Dict:
        return self.mock_analysis

    def process(self, data: Dict) -> Dict:
        """Process data according to BaseEngine requirements."""
        return {"processed": True, "data": data}


class BaseWorkflowIntegrationTest(ABC):
    """Base class for workflow integration tests."""

    # To be set by subclasses
    workflow_class: Type[Workflow] = None

    # Prevent pytest from collecting this class
    __test__ = False

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_companies_csv(self, temp_data_dir):
        """Create a sample companies CSV file."""
        csv_path = Path(temp_data_dir) / "exclude.csv"
        companies = [
            {
                "Company": "Test Corp A",
                "Symbol": "TCA",
                "Category": "Technology",
                "Criteria": "ESG",
            },
            {
                "Company": "Test Corp B",
                "Symbol": "TCB",
                "Category": "Healthcare",
                "Criteria": "Social Impact",
            },
        ]

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Company", "Symbol", "Category", "Criteria"]
            )
            writer.writeheader()
            writer.writerows(companies)

        return csv_path

    @pytest.fixture
    def mock_workflow(self, temp_data_dir):
        """Create a workflow instance with mock engines."""
        if self.workflow_class is None:
            raise NotImplementedError("Subclasses must set workflow_class")

        workflow = self.workflow_class()
        workflow.search_engine = MockSearchEngine()
        workflow.analysis_engine = MockAnalysisEngine()
        workflow.output_handler = ResearchOutputHandler(output_dir=temp_data_dir)
        return workflow

    def test_workflow_initialization(self, mock_workflow):
        """Test workflow initialization and component setup."""
        assert isinstance(mock_workflow.search_engine, BaseEngine)
        assert isinstance(mock_workflow.analysis_engine, BaseEngine)
        assert isinstance(mock_workflow.output_handler, ResearchOutputHandler)

    def test_workflow_execution(
        self, mock_workflow, temp_data_dir, sample_companies_csv
    ):
        """Test complete workflow execution."""
        results = mock_workflow.execute(data_dir=temp_data_dir)

        # Verify results structure
        assert isinstance(results, dict)
        assert "stats" in results
        assert "results" in results

        # Check stats
        stats = results["stats"]
        assert stats["companies_processed"] > 0
        assert stats["total_searches"] > 0
        assert stats["total_results"] > 0

        # Verify output files
        json_files = list(Path(temp_data_dir).glob("*.json"))
        assert len(json_files) > 0

        # Check JSON output structure
        with open(json_files[0]) as f:
            output_data = json.load(f)
            assert "meta" in output_data
            assert "companies" in output_data
            assert len(output_data["companies"]) > 0

    def test_database_integration(
        self, mock_workflow, temp_data_dir, sample_companies_csv
    ):
        """Test database operations during workflow execution."""
        mock_workflow.execute(data_dir=temp_data_dir)

        # Verify database file creation
        db_path = Path(temp_data_dir) / "research.db"
        assert db_path.exists()

    def test_error_handling(self, mock_workflow, temp_data_dir):
        """Test workflow error handling."""
        # Simulate missing input file
        with pytest.raises(FileNotFoundError):
            mock_workflow.execute(data_dir=temp_data_dir)

    def test_output_handler_integration(
        self, mock_workflow, temp_data_dir, sample_companies_csv
    ):
        """Test integration with output handler."""
        results = mock_workflow.execute(data_dir=temp_data_dir)

        # Verify output file format and content
        json_files = list(Path(temp_data_dir).glob("*.json"))
        assert len(json_files) == 1

        with open(json_files[0]) as f:
            output_data = json.load(f)

        # Check output structure
        assert "meta" in output_data
        assert output_data["meta"]["version"] == "1.0"
        assert "companies" in output_data

        # Verify company data
        companies = output_data["companies"]
        assert len(companies) > 0
        for company in companies:
            assert "company_name" in company
            assert "analysis" in company
            assert "metadata" in company

    def test_engine_integration(
        self, mock_workflow, temp_data_dir, sample_companies_csv
    ):
        """Test integration with search and analysis engines."""
        # Override mock engines with specific test data
        mock_workflow.search_engine = MockSearchEngine(
            [
                {
                    "title": "Custom Result",
                    "link": "http://test.com",
                    "snippet": "Test snippet",
                    "source": "Test source",
                }
            ]
        )
        mock_workflow.analysis_engine = MockAnalysisEngine(
            {"content": "Custom analysis", "summary": "Custom summary"}
        )

        results = mock_workflow.execute(data_dir=temp_data_dir)

        # Verify engine results in output
        json_files = list(Path(temp_data_dir).glob("*.json"))
        with open(json_files[0]) as f:
            output_data = json.load(f)

        company = output_data["companies"][0]
        assert "Custom Result" in str(company["analysis"]["evidence"]["sources"])
        assert "Custom analysis" in str(company["analysis"]["historical"])

    def setUp(self):
        init_db("sqlite:///:memory:")

    def tearDown(self):
        with get_connection(use_raw_cursor=True) as cursor:
            cursor.execute("YOUR TEARDOWN SQL HERE")
