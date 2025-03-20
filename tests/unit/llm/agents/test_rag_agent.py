"""Tests for the RAG agent."""

import pytest
from unittest.mock import patch, MagicMock
from dewey.llm.agents.rag_agent import RAGAgent
import warnings


@pytest.fixture
def config():
    """Provide a test configuration."""
    return {
        "llm": {
            "client": "test",
            "default_provider": "test",
            "providers": {
                "test": {"api_key": "test_key", "default_model": "test_model"}
            },
        },
        "agents": {"rag_search": {"enabled": True, "version": "1.0"}},
    }


@pytest.fixture
def mock_llm_handler():
    """Mock the LLMHandler."""
    mock = MagicMock()
    mock.get_model.return_value = "test_model"
    with patch("dewey.llm.agents.rag_agent.LLMHandler", return_value=mock):
        yield mock


@pytest.fixture
def rag_agent(config, mock_llm_handler):
    """Provide an initialized RAGAgent instance with mocked dependencies."""
    agent = RAGAgent(config=config)
    return agent


class TestRAGAgent:
    """Test suite for RAGAgent."""

    def test_initialization(self, rag_agent):
        """Test that RAGAgent initializes correctly."""
        assert isinstance(rag_agent, RAGAgent)
        assert rag_agent.task_type == "rag_search"

    def test_search_valid_input(self, rag_agent):
        """Test search with valid input."""
        query = "test query"
        content_type = "test_type"
        limit = 5

        # Mock the search tool
        mock_tool = MagicMock()
        mock_tool.name = "test_search"
        mock_tool.forward.return_value = [{"result": "test"}]
        rag_agent.tools = [mock_tool]

        results = rag_agent.search(query=query, content_type=content_type, limit=limit)
        assert len(results) == 1
        assert results[0]["result"] == "test"
        mock_tool.forward.assert_called_once_with(
            query=query, content_type=content_type, limit=limit
        )

    def test_search_without_content_type(self, rag_agent):
        """Test search without content type."""
        query = "test query"
        limit = 5

        # Mock the search tool
        mock_tool = MagicMock()
        mock_tool.name = "test_search"
        mock_tool.forward.return_value = [{"result": "test"}]
        rag_agent.tools = [mock_tool]

        results = rag_agent.search(query=query, limit=limit)
        assert len(results) == 1
        assert results[0]["result"] == "test"
        mock_tool.forward.assert_called_once_with(
            query=query, content_type=None, limit=limit
        )

    def test_search_uses_default_limit(self, rag_agent):
        """Test search uses default limit."""
        query = "test query"

        # Mock the search tool
        mock_tool = MagicMock()
        mock_tool.name = "test_search"
        mock_tool.forward.return_value = [{"result": "test"}]
        rag_agent.tools = [mock_tool]

        results = rag_agent.search(query=query)
        assert len(results) == 1
        mock_tool.forward.assert_called_once_with(
            query=query, content_type=None, limit=10
        )

    def test_search_negative_limit(self, rag_agent):
        """Test search with negative limit."""
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            rag_agent.search("test query", limit=-1)

    def test_search_non_integer_limit(self, rag_agent):
        """Test search with non-integer limit."""
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            rag_agent.search("test query", limit="5")

    def test_search_empty_query(self, rag_agent):
        """Test search with empty query."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            rag_agent.search("")


def test_deprecation_warning_emitted():
    """Test that a deprecation warning is emitted."""
    config = {
        "llm": {
            "client": "test",
            "default_provider": "test",
            "providers": {
                "test": {"api_key": "test_key", "default_model": "test_model"}
            },
        },
        "agents": {"rag_search": {"enabled": True, "version": "1.0"}},
    }
    with pytest.warns(DeprecationWarning, match="RAGAgent is deprecated"):
        RAGAgent(config=config)
