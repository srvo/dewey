"""Unit tests for the DeepSeek engine."""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dewey.core.research.engines.deepseek import (
    DeepSeekEngine,
    ResearchResult,
    SearchResult,
)


@pytest.fixture
def deepseek_engine() -> DeepSeekEngine:
    """Fixture for creating a DeepSeekEngine instance."""
    engine = DeepSeekEngine()
    engine.config = {
        "llm": {
            "providers": {
                "deepinfra": {"api_key": "test_api_key"}
            }
        }
    }
    engine.llm_client = AsyncMock()
    engine.logger = MagicMock()
    return engine


@pytest.fixture
def search_results() -> List[SearchResult]:
    """Fixture for creating a list of SearchResult instances."""
    return [
        SearchResult(url="http://example.com/1", content="Content 1"),
        SearchResult(url="http://example.com/2", content="Content 2"),
    ]


@pytest.fixture
def research_results() -> List[ResearchResult]:
    """Fixture for creating a list of ResearchResult instances."""
    return [ResearchResult(content="Sample research 1"), ResearchResult(content="Sample research 2")]


@pytest.mark.asyncio
async def test_analyze_with_results(deepseek_engine: DeepSeekEngine, search_results: List[SearchResult]) -> None:
    """Test analyze method with search results."""
    deepseek_engine.llm_client.generate.return_value = "LLM Response"
    result = await deepseek_engine.analyze(search_results, "test_template")
    assert isinstance(result, dict)
    assert "ethical_score" in result
    assert "llm_response" in result
    assert result["llm_response"] == "LLM Response"
    deepseek_engine.llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_no_results(deepseek_engine: DeepSeekEngine) -> None:
    """Test analyze method with no search results."""
    result = await deepseek_engine.analyze([], "test_template")
    assert result == {}
    deepseek_engine.llm_client.generate.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_api_key_from_config(deepseek_engine: DeepSeekEngine, search_results: List[SearchResult]) -> None:
    """Test analyze method retrieves API key from config."""
    deepseek_engine.llm_client.generate.return_value = "LLM Response"
    await deepseek_engine.analyze(search_results, "test_template")
    assert deepseek_engine.config["llm"]["providers"]["deepinfra"]["api_key"] == "test_api_key"


@pytest.mark.asyncio
async def test_conduct_research(deepseek_engine: DeepSeekEngine) -> None:
    """Test conduct_research method."""
    result = await deepseek_engine.conduct_research("initial query", ["follow up"])
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], ResearchResult)
    assert result[0].content == "Sample research"


def test_add_template(deepseek_engine: DeepSeekEngine) -> None:
    """Test add_template method."""
    template_name = "test_template"
    template_content = [{"role": "user", "content": "test"}]
    deepseek_engine.add_template(template_name, template_content)
    assert template_name in deepseek_engine.templates
    assert deepseek_engine.templates[template_name] == template_content


def test_run(deepseek_engine: DeepSeekEngine) -> None:
    """Test run method."""
    deepseek_engine.conduct_research = AsyncMock()
    deepseek_engine.run()
    deepseek_engine.conduct_research.assert_called_once()


def test_get_config_value(deepseek_engine: DeepSeekEngine) -> None:
    """Test get_config_value method."""
    value = deepseek_engine.get_config_value("llm.providers.deepinfra.api_key")
    assert value == "test_api_key"

    default_value = deepseek_engine.get_config_value("nonexistent.key", "default")
    assert default_value == "default"


def test_init(deepseek_engine: DeepSeekEngine) -> None:
    """Test the __init__ method."""
    assert deepseek_engine.name == "DeepSeekEngine"
    assert deepseek_engine.description == "Engine implementation using DeepSeek's API."
    assert deepseek_engine.config_section == "deepseek_engine"
    assert deepseek_engine.requires_db is False
    assert deepseek_engine.enable_llm is True
    assert deepseek_engine.templates == {}
