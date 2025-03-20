"""Tests for research analysis components."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from dewey.core.research.analysis.financial_analysis import FinancialAnalyzer
from dewey.core.research.analysis.ethical_analysis import EthicalAnalyzer

class TestFinancialAnalyzer:
    """Test suite for financial analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create a test financial analyzer instance."""
        return FinancialAnalyzer()

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        assert hasattr(analyzer, 'analyze_financials')
        assert hasattr(analyzer, 'calculate_metrics')

    def test_analyze_financials(self, analyzer):
        """Test financial analysis."""
        test_data = {
            "revenue": 1000000,
            "expenses": 800000,
            "assets": 2000000,
            "liabilities": 1000000
        }
        
        analysis = analyzer.analyze_financials(test_data)
        assert isinstance(analysis, dict)
        assert "profit_margin" in analysis
        assert "debt_ratio" in analysis
        assert analysis["profit_margin"] == pytest.approx(0.2)
        assert analysis["debt_ratio"] == pytest.approx(0.5)

    def test_calculate_metrics(self, analyzer):
        """Test financial metrics calculation."""
        test_data = {
            "cash_flow": 100000,
            "market_cap": 5000000,
            "shares_outstanding": 1000000
        }
        
        metrics = analyzer.calculate_metrics(test_data)
        assert isinstance(metrics, dict)
        assert "cash_flow_per_share" in metrics
        assert metrics["cash_flow_per_share"] == pytest.approx(0.1)

    def test_error_handling(self, analyzer):
        """Test error handling in financial analysis."""
        with pytest.raises(ValueError):
            analyzer.analyze_financials({})

class TestEthicalAnalyzer:
    """Test suite for ethical analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create a test ethical analyzer instance."""
        return EthicalAnalyzer()

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        assert hasattr(analyzer, 'analyze_ethics')
        assert hasattr(analyzer, 'calculate_esg_score')

    def test_analyze_ethics(self, analyzer):
        """Test ethical analysis."""
        test_data = {
            "environmental_impact": "low",
            "social_responsibility": "high",
            "governance_rating": "medium"
        }
        
        analysis = analyzer.analyze_ethics(test_data)
        assert isinstance(analysis, dict)
        assert "esg_score" in analysis
        assert "risk_assessment" in analysis
        assert 0 <= analysis["esg_score"] <= 100

    def test_calculate_esg_score(self, analyzer):
        """Test ESG score calculation."""
        test_data = {
            "environmental": 80,
            "social": 70,
            "governance": 90
        }
        
        score = analyzer.calculate_esg_score(test_data)
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score == pytest.approx(80.0)

    @patch('dewey.core.research.analysis.ethical_analysis.requests.get')
    def test_fetch_esg_data(self, mock_get, analyzer):
        """Test ESG data fetching."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "environmental": 75,
            "social": 85,
            "governance": 80
        }
        mock_get.return_value = mock_response
        
        data = analyzer.fetch_esg_data("COMPANY_XYZ")
        assert isinstance(data, dict)
        assert all(k in data for k in ["environmental", "social", "governance"])

@pytest.mark.integration
class TestAnalysisIntegration:
    """Integration tests for research analysis."""

    def test_combined_analysis_workflow(self):
        """Test complete analysis workflow combining financial and ethical analysis."""
        financial_analyzer = FinancialAnalyzer()
        ethical_analyzer = EthicalAnalyzer()
        
        # Test company data
        company_data = {
            "financials": {
                "revenue": 1000000,
                "expenses": 700000,
                "assets": 2000000,
                "liabilities": 900000
            },
            "esg_data": {
                "environmental_impact": "medium",
                "social_responsibility": "high",
                "governance_rating": "high"
            }
        }
        
        # Perform financial analysis
        financial_analysis = financial_analyzer.analyze_financials(company_data["financials"])
        assert isinstance(financial_analysis, dict)
        assert financial_analysis["profit_margin"] > 0
        
        # Perform ethical analysis
        ethical_analysis = ethical_analyzer.analyze_ethics(company_data["esg_data"])
        assert isinstance(ethical_analysis, dict)
        assert ethical_analysis["esg_score"] > 0
        
        # Combine analyses
        combined_analysis = {
            "financial": financial_analysis,
            "ethical": ethical_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
        assert "financial" in combined_analysis
        assert "ethical" in combined_analysis
        assert "timestamp" in combined_analysis 