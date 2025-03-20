# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dewey.core.research.workflows.ethical import EthicalAnalysisWorkflow
from dewey.core.research.analysis.ethical_analysis import (
    DeepSeekEngine,
    SearchResult,
    ResearchResult,
)

from tests.dewey.core.research.analysis.test_workflow_integration import (
    BaseEngine,
    BaseWorkflowIntegrationTest,
    MockAnalysisEngine,
    MockSearchEngine,
    ResearchOutputHandler,
)

# Mock DeepSeekEngine implementation for testing
class MockDeepSeekEngine(DeepSeekEngine):
    """Mock implementation for testing ethical analysis workflows."""
    
    def __init__(self):
        """Function __init__."""
        super().__init__()
        self.analyze_responses = {}
        self.research_responses = {}
    
    async def analyze(self, results: List[SearchResult], template_name: str) -> Dict[str, Any]:
        """Function analyze."""
        return self.analyze_responses.get(template_name, {})
    
    async def conduct_research(
        """Function conduct_research."""
        self,
        initial_query: str,
        follow_up_questions: List[str],
        context: Optional[Dict[str, Any]] = None,
        template_name: str = "default",
    ) -> List[ResearchResult]:
        return self.research_responses.get(template_name, [])

class MockSearchEngine(BaseEngine):
    """Mock search engine for testing."""
    
    def __init__(self, results):
        """Initialize with predefined results."""
        super().__init__()
        self.results = results
        self.templates = {}
    
    def search(self, query):
        """Return predefined results."""
        return self.results
    
    def add_template(self, name, template):
        """Store template."""
        self.templates[name] = template

class MockAnalysisEngine(BaseEngine):
    """Mock analysis engine for testing."""
    
    def __init__(self, result):
        """Initialize with predefined result."""
        super().__init__()
        self.result = result
        self.templates = {}
    
    def analyze(self, template_name, **kwargs):
        """Return predefined result."""
        if template_name == "ethical_analysis":
            return self.result.get("content", "")
        elif template_name == "risk_analysis":
            return self.result.get("summary", "")
        return self.result
    
    def add_template(self, name, template):
        """Store template."""
        self.templates[name] = template

# Mock MotherDuck engine for testing
class MockMotherDuckEngine:
    """Mock MotherDuck engine for testing."""
    
    def __init__(self):
        """Initialize with empty tables."""
        self.tables = {
            "research_searches": [],
            "research_search_results": [],
            "research_analyses": []
        }
        self.last_id = 0
    
    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Mock SQL execution."""
        if "CREATE TABLE" in sql:
            return None
        elif "INSERT INTO research_searches" in sql:
            self.last_id += 1
            search = {"id": self.last_id, **params}
            self.tables["research_searches"].append(search)
            return MagicMock(fetchone=lambda: [self.last_id])
        elif "INSERT INTO research_search_results" in sql:
            self.last_id += 1
            result = {"id": self.last_id, **params}
            self.tables["research_search_results"].append(result)
            return None
        elif "INSERT INTO research_analyses" in sql:
            self.last_id += 1
            analysis = {"id": self.last_id, **params}
            self.tables["research_analyses"].append(analysis)
            return None
        elif "UPDATE research_searches" in sql:
            search = next(s for s in self.tables["research_searches"] if s["id"] == params["id"])
            search["num_results"] = params["num_results"]
            return None
        return None

@pytest.fixture
def mock_engine():
    """Create a mock DeepSeek engine."""
    return MockDeepSeekEngine()

@pytest.fixture
def mock_db():
    """Create a mock MotherDuck database."""
    return MockMotherDuckEngine()

@pytest.fixture
def mock_workflow(tmp_path, mock_db):
    """Create a mock workflow with test engines."""
    search_engine = MockSearchEngine([
        {
            "title": "Test Result",
            "link": "http://test.com",
            "snippet": "Test snippet",
            "source": "Test source",
        }
    ])
    analysis_engine = MockAnalysisEngine({
        "content": "Test analysis",
        "summary": "Test summary",
        "historical": "Test history",
    })
    output_handler = ResearchOutputHandler()
    
    with patch("dewey.core.research.workflows.ethical.MotherDuckEngine", return_value=mock_db):
        workflow = EthicalAnalysisWorkflow(
            data_dir=tmp_path,
            search_engine=search_engine,
            analysis_engine=analysis_engine,
            output_handler=output_handler,
        )
        return workflow

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory with test files."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(parents=True)
    
    # Create test companies.csv
    companies_csv = data_dir / "companies.csv"
    companies_csv.write_text(
        "Company,Category,Criteria\n"
        "Test Company 1,Test,Test Criteria 1\n"
        "Test Company 2,Test,Test Criteria 2\n"
    )
    return data_dir

@pytest.fixture
def sample_companies_csv(temp_data_dir):
    """Return path to sample companies CSV file."""
    return temp_data_dir / "companies.csv"

@pytest.fixture
def workflow(tmp_path, mock_db):
    """Create a workflow instance for testing."""
    with patch("dewey.core.research.workflows.ethical.MotherDuckEngine", return_value=mock_db):
        workflow = EthicalAnalysisWorkflow(
            data_dir=str(tmp_path),
            search_engine=MockSearchEngine([
                {
                    "title": "Test Result",
                    "link": "http://test.com",
                    "snippet": "Test snippet",
                    "source": "Test source",
                }
            ]),
            analysis_engine=MockAnalysisEngine({
                "content": "Test analysis",
                "summary": "Test summary",
                "historical": "Test history",
            }),
            output_handler=ResearchOutputHandler(output_dir=str(tmp_path))
        )
        return workflow

class TestEthicalAnalysisWorkflow(BaseWorkflowIntegrationTest):
    """Integration tests for EthicalAnalysisWorkflow."""

    workflow_class = EthicalAnalysisWorkflow
    __test__ = True

    def test_workflow_initialization(self, mock_workflow) -> None:
        """Test workflow initialization and component setup."""
        assert isinstance(mock_workflow.search_engine, BaseEngine)
        assert isinstance(mock_workflow.analysis_engine, BaseEngine)
        assert isinstance(mock_workflow.output_handler, ResearchOutputHandler)

    def test_workflow_execution(
        self,
        mock_workflow,
        temp_data_dir,
        sample_companies_csv,
    ) -> None:
        """Test complete workflow execution."""
        results = mock_workflow.execute(data_dir=temp_data_dir)

        # Verify results structure
        assert isinstance(results, dict)
        assert "stats" in results
        assert "results" in results

        # Check stats
        stats = results["stats"]
        assert stats["companies_processed"] == 2
        assert stats["total_searches"] == 2
        assert stats["total_results"] == 2

        # Verify output files
        json_files = list(Path(temp_data_dir).glob("*.json"))
        assert len(json_files) == 1

        # Check JSON output structure
        with open(json_files[0]) as f:
            output_data = json.load(f)
            assert "meta" in output_data
            assert "companies" in output_data
            assert len(output_data["companies"]) == 2

    def test_database_integration(
        self,
        mock_workflow,
        mock_db,
        temp_data_dir,
        sample_companies_csv,
    ) -> None:
        """Test database operations during workflow execution."""
        mock_workflow.execute(data_dir=temp_data_dir)

        # Verify data was stored in tables
        assert len(mock_db.tables["research_searches"]) > 0
        assert len(mock_db.tables["research_search_results"]) > 0
        assert len(mock_db.tables["research_analyses"]) > 0

        # Verify search data
        search = mock_db.tables["research_searches"][0]
        assert "query" in search
        assert "num_results" in search
        assert search["num_results"] > 0

        # Verify search results
        result = mock_db.tables["research_search_results"][0]
        assert "title" in result
        assert "link" in result
        assert "snippet" in result
        assert "source" in result

        # Verify analysis data
        analysis = mock_db.tables["research_analyses"][0]
        assert "company" in analysis
        assert "content" in analysis
        assert "summary" in analysis
        assert "ethical_score" in analysis
        assert "risk_level" in analysis

    def test_error_handling(self, mock_workflow, temp_data_dir) -> None:
        """Test workflow error handling."""
        # Simulate missing input file
        with pytest.raises(FileNotFoundError):
            mock_workflow.execute(data_dir=temp_data_dir)

    def test_output_handler_integration(
        self,
        mock_workflow,
        temp_data_dir,
        sample_companies_csv,
    ) -> None:
        """Test integration with output handler."""
        mock_workflow.execute(data_dir=temp_data_dir)

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
        assert len(companies) == 2
        for company in companies:
            assert "company_name" in company
            assert "metadata" in company
            assert "analysis" in company
            assert "evidence" in company["analysis"]
            assert "sources" in company["analysis"]["evidence"]

    def test_engine_integration(
        self,
        mock_workflow,
        temp_data_dir,
        sample_companies_csv,
    ) -> None:
        """Test integration with search and analysis engines."""
        # Override mock engines with specific test data
        mock_workflow.search_engine = MockSearchEngine([
            {
                "title": "Custom Result",
                "link": "http://test.com",
                "snippet": "Test snippet",
                "source": "Test source",
            }
        ])
        mock_workflow.analysis_engine = MockAnalysisEngine({
            "content": "Custom analysis",
            "summary": "Custom summary",
            "historical": "Custom history",
        })

        mock_workflow.execute(data_dir=temp_data_dir)

        # Verify engine results in output
        json_files = list(Path(temp_data_dir).glob("*.json"))
        with open(json_files[0]) as f:
            output_data = json.load(f)

        company = output_data["companies"][0]
        assert company["analysis"]["summary"] == "Custom summary"
        assert company["analysis"]["historical"] == "Custom history"
        assert company["analysis"]["evidence"]["sources"][0]["title"] == "Custom Result"

    def test_query_building(self, mock_workflow) -> None:
        """Test company query building."""
        test_company = {
            "Company": "Test Corp",
            "Category": "Technology",
            "Criteria": "ESG",
        }

        query = mock_workflow.build_query(test_company)

        # Verify query components
        assert "Test Corp" in query
        assert "Technology" in query
        assert "ESG" in query
        assert "ethical" in query
        assert "controversies" in query
        assert "violations" in query

    def test_word_counting(self, mock_workflow) -> None:
        """Test word count functionality."""
        text = "This is a test sentence with seven words"  # Actually 8 words
        assert mock_workflow.word_count(text) == 8

        # Test edge cases
        assert mock_workflow.word_count("") == 0
        assert mock_workflow.word_count(None) == 0
        assert mock_workflow.word_count("Single") == 1

    def test_database_schema(self, mock_workflow, temp_data_dir) -> None:
        """Test database schema creation and validation."""
        db_path = Path(temp_data_dir) / "test.db"
        con = mock_workflow.setup_database(db_path)

        # Verify tables exist
        tables = con.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
        """,
        ).fetchall()

        table_names = [t[0] for t in tables]
        assert "research_searches" in table_names
        assert "research_search_results" in table_names
        assert "research_analyses" in table_names

        # Verify table schemas
        searches_schema = con.execute("PRAGMA table_info(research_searches)").fetchall()
        assert any(col[1] == "timestamp" for col in searches_schema)
        assert any(col[1] == "query" for col in searches_schema)
        assert any(col[1] == "num_results" for col in searches_schema)

        results_schema = con.execute("PRAGMA table_info(research_search_results)").fetchall()
        assert any(col[1] == "timestamp" for col in results_schema)
        assert any(col[1] == "title" for col in results_schema)
        assert any(col[1] == "link" for col in results_schema)
        assert any(col[1] == "snippet" for col in results_schema)

        con.close()

    def test_workflow_stats(
        self,
        mock_workflow,
        temp_data_dir,
        sample_companies_csv,
    ) -> None:
        """Test statistics generation during workflow execution."""
        results = mock_workflow.execute(data_dir=temp_data_dir)
        stats = results["stats"]

        # Verify all expected stats are present
        assert "companies_processed" in stats
        assert "total_searches" in stats
        assert "total_results" in stats
        assert "total_snippet_words" in stats
        assert "total_analyses" in stats
        assert "total_analysis_words" in stats

        # Verify stats are consistent
        assert stats["companies_processed"] == 2  # From sample_companies_csv
        assert stats["total_searches"] == stats["companies_processed"]
        assert stats["total_results"] == 2  # One result per company
        assert stats["total_snippet_words"] > 0
        assert stats["total_analyses"] == stats["companies_processed"]
        assert stats["total_analysis_words"] > 0

    def test_error_recovery(
        self,
        mock_workflow,
        temp_data_dir,
        sample_companies_csv,
    ) -> None:
        """Test workflow continues after individual company errors."""

        # Create a search engine that fails for specific companies
        class FailingSearchEngine:
            """Class FailingSearchEngine."""
            def search(self, query):
                """Function search."""
                if "Test Company 1" in query:
                    raise Exception("Simulated search failure")
                return [
                    {
                        "title": "Result",
                        "link": "http://test.com",
                        "snippet": "Test",
                        "source": "Test",
                    }
                ]

        mock_workflow.search_engine = FailingSearchEngine()

        # Execute workflow - should continue despite error
        results = mock_workflow.execute(data_dir=temp_data_dir)

        # Verify partial results
        assert results["stats"]["companies_processed"] == 2
        assert len(results["results"]) == 1  # Only one company should succeed

        # Check output file still contains valid data
        json_files = list(Path(temp_data_dir).glob("*.json"))
        with open(json_files[0]) as f:
            output_data = json.load(f)

        # Should still have valid company data for the successful company
        assert len(output_data["companies"]) == 1
        assert output_data["companies"][0]["company_name"] == "Test Company 2"

    def test_init_templates(self, workflow: EthicalAnalysisWorkflow):
        """Verify templates are properly initialized."""
        assert "ethical_analysis" in workflow.engine.templates
        assert "risk_analysis" in workflow.engine.templates
        
    async def test_analyze_company_profile_valid(self, workflow: EthicalAnalysisWorkflow):
        """Test successful analysis with valid search results."""
        results = [SearchResult(url="test.com", content="test data")]
        analysis = await workflow.analyze_company_profile(results)
        assert isinstance(analysis, dict)
        assert "ethical_score" in analysis
    
    async def test_analyze_company_profile_no_results(self, workflow: EthicalAnalysisWorkflow):
        """Test analysis with empty search results."""
        results = []
        analysis = await workflow.analyze_company_profile(results)
        assert analysis == {}
    
    async def test_assess_risks_valid(self, workflow: EthicalAnalysisWorkflow):
        """Test successful risk assessment."""
        results = [SearchResult(url="test.com", content="test data")]
        risks = await workflow.assess_risks(results)
        assert "risk_level" in risks
    
    async def test_conduct_research_valid(self, workflow: EthicalAnalysisWorkflow):
        """Test successful deep research with follow-up questions."""
        research = await workflow.conduct_deep_research(
            "Test query",
            ["Question 1", "Question 2"],
            context={"key": "value"}
        )
        assert isinstance(research, list)
        assert all(isinstance(r, ResearchResult) for r in research)
    
    async def test_conduct_research_no_followups(self, workflow: EthicalAnalysisWorkflow):
        """Test research with no follow-up questions."""
        research = await workflow.conduct_deep_research("Test query", [])
        assert len(research) == 1  # Should have initial analysis
    
    async def test_engine_error_handling(self, workflow: EthicalAnalysisWorkflow, caplog):
        """Test error handling for engine exceptions."""
        workflow.engine.analyze = AsyncMock(side_effect=Exception("Test error"))
        
        try:
            await workflow.analyze_company_profile([])
        except Exception:
            assert "Error performing ethical analysis" in caplog.text
