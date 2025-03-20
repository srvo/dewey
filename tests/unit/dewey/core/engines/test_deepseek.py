"""Unit tests for the DeepSeek engine."""

import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.engines.deepseek import DeepSeekEngine
from dewey.core.base_script import BaseScript


class TestDeepSeekEngine:
    """Unit tests for the DeepSeekEngine class."""

    @pytest.fixture
    def deepseek_engine(self) -> DeepSeekEngine:
        """Fixture to create a DeepSeekEngine instance."""
        engine = DeepSeekEngine()
        engine.logger = MagicMock()  # Mock the logger
        engine.llm_client = MagicMock()  # Mock the llm_client
        return engine

    def test_init(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the __init__ method."""
        assert isinstance(deepseek_engine, DeepSeekEngine)
        assert isinstance(deepseek_engine.templates, dict)
        assert "ethical_analysis" in deepseek_engine.templates
        assert "risk_assessment" in deepseek_engine.templates

    def test_run_not_implemented(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test that the run method raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="The run method must be implemented"):
            deepseek_engine.run()
        deepseek_engine.logger.info.assert_called_with("DeepSeek engine started.")

    def test_search(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the search method."""
        query = "test query"
        results = deepseek_engine.search(query)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert results[0]["title"] == "Test Result"
        deepseek_engine.logger.info.assert_called_with(f"Searching for: {query}")

    def test_analyze_with_template(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method with a valid template."""
        content = "test content"
        template = "ethical_analysis"
        deepseek_engine.llm_client.generate_response.return_value = "Test response"
        results = deepseek_engine.analyze(content, template, company="Test Company")
        assert isinstance(results, dict)
        assert "content" in results
        assert results["content"] == "Test response"
        deepseek_engine.logger.info.assert_called_with(f"Analyzing content with template: {template}")
        deepseek_engine.llm_client.generate_response.assert_called()

    def test_analyze_without_template(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method without a template."""
        content = "test content"
        deepseek_engine.llm_client.generate_response.return_value = "Test response"
        results = deepseek_engine.analyze(content)
        assert isinstance(results, dict)
        assert "content" in results
        deepseek_engine.logger.info.assert_called_with("Analyzing content with template: None")
        deepseek_engine.llm_client.generate_response.assert_called()

    def test_analyze_template_not_found(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method when the template is not found."""
        content = "test content"
        template = "invalid_template"
        deepseek_engine.llm_client.generate_response.return_value = "Test response"
        results = deepseek_engine.analyze(content, template)
        assert isinstance(results, dict)
        assert "content" in results
        deepseek_engine.logger.warning.assert_called_with(
            f"Template '{template}' not found. Using default analysis."
        )
        deepseek_engine.llm_client.generate_response.assert_called()

    def test_analyze_error_during_analysis(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method when an error occurs during analysis."""
        content = "test content"
        template = "ethical_analysis"
        deepseek_engine.llm_client.generate_response.side_effect = Exception("Test error")
        results = deepseek_engine.analyze(content, template, company="Test Company")
        assert isinstance(results, dict)
        assert not results
        deepseek_engine.logger.error.assert_called()

    def test_analyze_empty_content(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method with empty content."""
        content = ""
        template = "ethical_analysis"
        deepseek_engine.llm_client.generate_response.return_value = "Test response"
        results = deepseek_engine.analyze(content, template, company="Test Company")
        assert isinstance(results, dict)
        assert "content" in results
        assert results["content"] == "Test response"
        deepseek_engine.llm_client.generate_response.assert_called()

    def test_analyze_no_kwargs(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method with no kwargs."""
        content = "test content"
        template = "risk_assessment"
        deepseek_engine.llm_client.generate_response.return_value = "Test response"
        results = deepseek_engine.analyze(content, template)
        assert isinstance(results, dict)
        assert "content" in results
        deepseek_engine.llm_client.generate_response.assert_called()

    def test_analyze_with_kwargs(self, deepseek_engine: DeepSeekEngine) -> None:
        """Test the analyze method with kwargs."""
        content = "test content"
        template = "risk_assessment"
        deepseek_engine.llm_client.generate_response.return_value = "Test response"
        results = deepseek_engine.analyze(content, template, company="Test Company", industry="Tech")
        assert isinstance(results, dict)
        assert "content" in results
        deepseek_engine.llm_client.generate_response.assert_called()
