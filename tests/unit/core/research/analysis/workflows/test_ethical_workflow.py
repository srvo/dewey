"""Tests for ethical analysis workflow."""

import pytest
from unittest.mock import patch
from datetime import datetime
from dewey.core.research.analysis.ethical_analysis import EthicalAnalysisWorkflow
from dewey.core.research.analysis.ethical_analyzer import EthicalAnalyzer


class TestEthicalAnalysisWorkflow:
    """Test suite for EthicalAnalysisWorkflow."""

    @pytest.fixture
    def workflow(self, mock_llm_handler):
        """Create a workflow instance with mocked dependencies."""
        return EthicalAnalysisWorkflow(llm_handler=mock_llm_handler)

    def test_init_templates(self, workflow):
        """Test template initialization."""
        assert hasattr(workflow, "templates")
        assert "ethical_analysis" in workflow.templates
        assert "risk_analysis" in workflow.templates

    async def test_analyze_company_profile(self, workflow, mock_search_results):
        """Test company profile analysis."""
        result = await workflow.analyze_company_profile(mock_search_results)
        assert isinstance(result, dict)
        assert "analysis" in result
        assert "ethical_score" in result
        assert "risk_level" in result

    async def test_assess_risks(self, workflow, mock_search_results):
        """Test risk assessment."""
        result = await workflow.assess_risks(mock_search_results)
        assert isinstance(result, dict)
        assert "analysis" in result
        assert "risk_level" in result

    async def test_conduct_deep_research(self, workflow):
        """Test deep research functionality."""
        follow_up_questions = [
            "What are the environmental impacts?",
            "Are there labor issues?",
        ]
        results = await workflow.conduct_deep_research(
            initial_query="Test Corp ethical analysis",
            follow_up_questions=follow_up_questions,
        )
        assert isinstance(results, list)
        assert len(results) > 0


class TestEthicalAnalyzer:
    """Test suite for EthicalAnalyzer."""

    @pytest.fixture
    def analyzer(self, tmp_data_dir, mock_db_connection, mock_llm_handler):
        """Create an analyzer instance with mocked dependencies."""
        with patch(
            "dewey.core.research.analysis.ethical_analyzer.get_connection",
            return_value=mock_db_connection,
        ):
            return EthicalAnalyzer(data_dir=tmp_data_dir)

    def test_setup_analysis_tables(self, analyzer, mock_db_connection):
        """Test database table setup."""
        analyzer.setup_analysis_tables()
        mock_db_connection.cursor().execute.assert_called()
        assert mock_db_connection.commit.called

    def test_generate_analysis_prompt(self, analyzer):
        """Test analysis prompt generation."""
        company_row = {
            "Company": "Test Corp",
            "Symbol": "TEST",
            "Category": "Product-based",
            "Criteria": "Animal Cruelty",
        }
        prompt = analyzer.generate_analysis_prompt(company_row)
        assert "Test Corp (TEST)" in prompt
        assert "Product-based - Animal Cruelty" in prompt
        assert "HISTORICAL ANALYSIS" in prompt

    def test_save_analysis_json(self, analyzer, tmp_data_dir):
        """Test JSON saving functionality."""
        company_data = {
            "meta": {"type": "ethical_analysis"},
            "companies": [{"name": "Test Corp"}],
        }
        timestamp = datetime.now()
        analyzer.save_analysis_json(company_data, timestamp)

        json_dir = tmp_data_dir / "analysis_json"
        assert json_dir.exists()
        json_files = list(json_dir.glob("ethical_analysis_*.json"))
        assert len(json_files) == 1

    def test_run_analysis_with_data(self, analyzer, sample_companies_csv):
        """Test full analysis run with sample data."""
        results = analyzer.run_analysis()
        assert results["meta"]["type"] == "ethical_analysis"
        assert len(results["companies"]) > 0
        assert results["companies"][0]["name"] == "Test Corp"

    def test_run_analysis_empty_data(self, analyzer, tmp_data_dir):
        """Test analysis run with empty data."""
        empty_csv = tmp_data_dir / "exclude.csv"
        empty_csv.write_text("Company,Symbol,Category,Criteria\n")

        results = analyzer.run_analysis()
        assert len(results["companies"]) == 0

    def test_run_analysis_missing_file(self, analyzer):
        """Test error handling for missing input file."""
        with pytest.raises(FileNotFoundError):
            analyzer.run_analysis()

    @pytest.mark.integration
    def test_full_workflow_integration(
        self, analyzer, sample_companies_csv, mock_db_connection
    ):
        """Integration test for full analysis workflow."""
        # Setup database
        analyzer.setup_analysis_tables()

        # Run analysis
        results = analyzer.run_analysis()

        # Verify results
        assert results["meta"]["type"] == "ethical_analysis"
        assert len(results["companies"]) > 0

        # Check database interactions
        mock_db_connection.cursor().execute.assert_called()
        assert mock_db_connection.commit.called
