"""Tests for research engines."""

import pytest
from unittest.mock import Mock, patch
from dewey.core.research.engines.base import BaseResearchEngine
from dewey.core.research.engines.deepseek import DeepseekEngine


class TestBaseResearchEngine:
    """Test suite for base research engine."""

    @pytest.fixture
    def engine(self):
        """Create a test engine instance."""
        return BaseResearchEngine()

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert hasattr(engine, "process_query")
        assert hasattr(engine, "analyze_results")

    def test_process_query(self, engine):
        """Test query processing."""
        with pytest.raises(NotImplementedError):
            engine.process_query("test query")

    def test_analyze_results(self, engine):
        """Test results analysis."""
        with pytest.raises(NotImplementedError):
            engine.analyze_results({"test": "data"})


class TestDeepseekEngine:
    """Test suite for Deepseek engine."""

    @pytest.fixture
    def engine(self):
        """Create a test Deepseek engine instance."""
        return DeepseekEngine()

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert isinstance(engine, BaseResearchEngine)

    @patch("dewey.core.research.engines.deepseek.requests.post")
    def test_process_query(self, mock_post, engine):
        """Test query processing with Deepseek."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "test result"}
        mock_post.return_value = mock_response

        result = engine.process_query("test query")
        assert result == {"result": "test result"}
        mock_post.assert_called_once()

    def test_analyze_results(self, engine):
        """Test results analysis."""
        test_data = {
            "result": "Company XYZ shows strong financial performance",
            "confidence": 0.85,
        }
        analysis = engine.analyze_results(test_data)
        assert isinstance(analysis, dict)
        assert "summary" in analysis
        assert "confidence_score" in analysis

    @patch("dewey.core.research.engines.deepseek.requests.post")
    def test_error_handling(self, mock_post, engine):
        """Test error handling in API calls."""
        mock_post.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            engine.process_query("test query")
        assert "API Error" in str(exc_info.value)


@pytest.mark.integration
class TestEngineIntegration:
    """Integration tests for research engines."""

    def test_engine_workflow(self):
        """Test complete engine workflow."""
        engine = DeepseekEngine()

        # Test query processing
        query = "Analyze financial performance of Company XYZ"
        with patch("dewey.core.research.engines.deepseek.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "result": "Strong financial performance",
                "confidence": 0.9,
            }
            mock_post.return_value = mock_response

            result = engine.process_query(query)
            assert result is not None

            # Test analysis
            analysis = engine.analyze_results(result)
            assert isinstance(analysis, dict)
            assert analysis.get("confidence_score", 0) >= 0.8
