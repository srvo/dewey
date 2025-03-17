import pytest
from pathlib import Path
import json
from ethifinx.research.workflows.ethical import EthicalAnalysisWorkflow
from .test_workflow_integration import (
    BaseWorkflowIntegrationTest,
    BaseEngine,
    ResearchOutputHandler,
    MockSearchEngine,
    MockAnalysisEngine,
)


class TestEthicalAnalysisWorkflow(BaseWorkflowIntegrationTest):
    """Integration tests for EthicalAnalysisWorkflow."""

    workflow_class = EthicalAnalysisWorkflow
    __test__ = True

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

    def test_query_building(self, mock_workflow):
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

    def test_word_counting(self, mock_workflow):
        """Test word count functionality."""
        text = "This is a test sentence with seven words"  # Actually 8 words
        assert mock_workflow.word_count(text) == 8

        # Test edge cases
        assert mock_workflow.word_count("") == 0
        assert mock_workflow.word_count(None) == 0
        assert mock_workflow.word_count("Single") == 1

    def test_database_schema(self, mock_workflow, temp_data_dir):
        """Test database schema creation and validation."""
        db_path = Path(temp_data_dir) / "test.db"
        con = mock_workflow.setup_database(db_path)

        # Verify tables exist
        tables = con.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """
        ).fetchall()

        table_names = [t[0] for t in tables]
        assert "searches" in table_names
        assert "search_results" in table_names
        assert "analyses" in table_names

        # Verify table schemas
        searches_schema = con.execute("PRAGMA table_info(searches)").fetchall()
        assert any(col[1] == "timestamp" for col in searches_schema)
        assert any(col[1] == "query" for col in searches_schema)
        assert any(col[1] == "num_results" for col in searches_schema)

        results_schema = con.execute("PRAGMA table_info(search_results)").fetchall()
        assert any(col[1] == "timestamp" for col in results_schema)
        assert any(col[1] == "title" for col in results_schema)
        assert any(col[1] == "link" for col in results_schema)
        assert any(col[1] == "snippet" for col in results_schema)

        con.close()

    def test_workflow_stats(self, mock_workflow, temp_data_dir, sample_companies_csv):
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
        assert stats["total_results"] > 0
        assert stats["total_snippet_words"] > 0
        assert stats["total_analyses"] == stats["companies_processed"]
        assert stats["total_analysis_words"] > 0

    def test_error_recovery(self, mock_workflow, temp_data_dir, sample_companies_csv):
        """Test workflow continues after individual company errors."""

        # Create a search engine that fails for specific companies
        class FailingSearchEngine:
            def search(self, query):
                if "Test Corp A" in query:
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
        assert output_data["companies"][0]["company_name"] == "Test Corp B"
