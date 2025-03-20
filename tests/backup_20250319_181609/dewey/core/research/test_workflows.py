"""Tests for research workflows."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from dewey.core.research.workflows.ethical import EthicalWorkflow

class TestEthicalWorkflow:
    """Test suite for ethical research workflow."""

    @pytest.fixture
    def workflow(self):
        """Create a test workflow instance."""
        return EthicalWorkflow()

    def test_initialization(self, workflow):
        """Test workflow initialization."""
        assert workflow is not None
        assert hasattr(workflow, 'run')
        assert hasattr(workflow, 'analyze')

    @patch('dewey.core.research.workflows.ethical.EthicalAnalyzer')
    def test_run_workflow(self, mock_analyzer, workflow):
        """Test running the workflow."""
        # Mock analyzer
        mock_instance = Mock()
        mock_instance.analyze_ethics.return_value = {
            "esg_score": 85,
            "risk_assessment": "low",
            "recommendations": ["Improve environmental reporting"]
        }
        mock_analyzer.return_value = mock_instance

        # Test data
        company_data = {
            "name": "Test Company",
            "sector": "Technology",
            "esg_data": {
                "environmental_impact": "medium",
                "social_responsibility": "high",
                "governance_rating": "high"
            }
        }

        result = workflow.run(company_data)
        assert isinstance(result, dict)
        assert "esg_score" in result
        assert "risk_assessment" in result
        assert "recommendations" in result
        assert result["esg_score"] == 85

    def test_analyze_results(self, workflow):
        """Test results analysis."""
        test_results = {
            "esg_score": 75,
            "risk_assessment": "medium",
            "recommendations": ["Improve sustainability practices"]
        }

        analysis = workflow.analyze(test_results)
        assert isinstance(analysis, dict)
        assert "summary" in analysis
        assert "action_items" in analysis
        assert isinstance(analysis["action_items"], list)

    def test_validation(self, workflow):
        """Test input validation."""
        invalid_data = {
            "name": "Test Company"
            # Missing required fields
        }

        with pytest.raises(ValueError):
            workflow.run(invalid_data)

    @patch('dewey.core.research.workflows.ethical.EthicalAnalyzer')
    def test_error_handling(self, mock_analyzer, workflow):
        """Test error handling."""
        mock_instance = Mock()
        mock_instance.analyze_ethics.side_effect = Exception("Analysis failed")
        mock_analyzer.return_value = mock_instance

        with pytest.raises(Exception) as exc_info:
            workflow.run({"name": "Test Company"})
        assert "Analysis failed" in str(exc_info.value)

@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests for research workflows."""

    def test_complete_workflow(self):
        """Test complete workflow execution."""
        workflow = EthicalWorkflow()

        # Test company data
        company_data = {
            "name": "Integration Test Corp",
            "sector": "Technology",
            "esg_data": {
                "environmental_impact": "medium",
                "social_responsibility": "high",
                "governance_rating": "high"
            },
            "financial_data": {
                "revenue": 1000000,
                "expenses": 700000
            }
        }

        with patch('dewey.core.research.workflows.ethical.EthicalAnalyzer') as mock_analyzer:
            # Mock analyzer response
            mock_instance = Mock()
            mock_instance.analyze_ethics.return_value = {
                "esg_score": 85,
                "risk_assessment": "low",
                "recommendations": ["Continue current practices"]
            }
            mock_analyzer.return_value = mock_instance

            # Run workflow
            result = workflow.run(company_data)
            assert isinstance(result, dict)
            assert result["esg_score"] >= 0

            # Analyze results
            analysis = workflow.analyze(result)
            assert isinstance(analysis, dict)
            assert "summary" in analysis
            assert "action_items" in analysis

            # Verify workflow output format
            assert "timestamp" in result
            assert datetime.fromisoformat(result["timestamp"])
            assert "company_name" in result
            assert result["company_name"] == "Integration Test Corp" 