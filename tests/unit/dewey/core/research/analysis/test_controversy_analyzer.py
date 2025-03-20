"""Unit tests for the ControversyAnalyzer class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from dewey.core.research.analysis.controversy_analyzer import ControversyAnalyzer


@pytest.fixture
def controversy_analyzer() -> ControversyAnalyzer:
    """Fixture to create a ControversyAnalyzer instance."""
    analyzer = ControversyAnalyzer()
    analyzer.searxng_url = "https://mocksearxng.com"  # Override URL for testing
    return analyzer


@pytest.mark.asyncio
async def test_search_controversies_success(controversy_analyzer: ControversyAnalyzer):
    """Test successful search for controversies."""
    entity = "TestEntity"
    mock_response = httpx.Response(
        200, json={"results": [{"title": "Test Controversy", "url": "http://example.com"}]}
    )
    controversy_analyzer.logger = MagicMock()
    async with httpx.AsyncClient() as client:
        client.get = AsyncMock(return_value=mock_response)
        controversy_analyzer.search_controversies.__self__ = controversy_analyzer
        results = await controversy_analyzer.search_controversies(entity)

    assert len(results) == 4  # Four queries are made
    assert all(isinstance(result, dict) for result in results)
    assert "title" in results[0]
    assert "url" in results[0]


@pytest.mark.asyncio
async def test_search_controversies_failure(controversy_analyzer: ControversyAnalyzer):
    """Test handling of failed search requests."""
    entity = "TestEntity"
    mock_response = httpx.Response(500)
    controversy_analyzer.logger = MagicMock()
    async with httpx.AsyncClient() as client:
        client.get = AsyncMock(return_value=mock_response)
        controversy_analyzer.search_controversies.__self__ = controversy_analyzer
        results = await controversy_analyzer.search_controversies(entity)

    assert len(results) == 4  # Four queries are made
    assert results == [None, None, None, None]
    controversy_analyzer.logger.warning.assert_called()


@pytest.mark.asyncio
async def test_search_controversies_exception(controversy_analyzer: ControversyAnalyzer):
    """Test handling of exceptions during search requests."""
    entity = "TestEntity"
    controversy_analyzer.logger = MagicMock()
    async with httpx.AsyncClient() as client:
        client.get = AsyncMock(side_effect=Exception("Test Exception"))
        controversy_analyzer.search_controversies.__self__ = controversy_analyzer
        results = await controversy_analyzer.search_controversies(entity)

    assert len(results) == 4  # Four queries are made
    assert results == [None, None, None, None]
    controversy_analyzer.logger.error.assert_called()


@pytest.mark.asyncio
async def test_analyze_sources_success(controversy_analyzer: ControversyAnalyzer):
    """Test successful analysis and categorization of sources."""
    results = [
        {"url": "http://reuters.com/article1", "title": "News 1"},
        {"url": "http://twitter.com/user1/status1", "title": "Tweet 1"},
        {"url": "http://sec.gov/document1", "title": "SEC Filing 1"},
        {"url": "http://example.com/other1", "title": "Other 1"},
    ]
    controversy_analyzer.categorize_source = AsyncMock(
        side_effect=["news", "social_media", "regulatory", "other"]
    )
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.analyze_sources.__self__ = controversy_analyzer
    sources = await controversy_analyzer.analyze_sources(results)

    assert isinstance(sources, dict)
    assert set(sources.keys()) == {"news", "social_media", "regulatory", "academic", "other"}
    assert len(sources["news"]) == 1
    assert len(sources["social_media"]) == 1
    assert len(sources["regulatory"]) == 1
    assert len(sources["other"]) == 1
    assert len(sources["academic"]) == 0
    controversy_analyzer.categorize_source.assert_called()


@pytest.mark.asyncio
async def test_analyze_sources_exception(controversy_analyzer: ControversyAnalyzer):
    """Test handling of exceptions during source analysis."""
    results = [{"url": "http://example.com/article1", "title": "Article 1"}]
    controversy_analyzer.categorize_source = AsyncMock(side_effect=Exception("Test Exception"))
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.analyze_sources.__self__ = controversy_analyzer
    sources = await controversy_analyzer.analyze_sources(results)

    assert isinstance(sources, dict)
    assert set(sources.keys()) == {"news", "social_media", "regulatory", "academic", "other"}
    assert len(sources["news"]) == 0
    controversy_analyzer.logger.error.assert_called()


@pytest.mark.asyncio
async def test_categorize_source_news(controversy_analyzer: ControversyAnalyzer):
    """Test categorization of a news source."""
    url = "http://reuters.com/article1"
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    category = await controversy_analyzer.categorize_source(url)
    assert category == "news"


@pytest.mark.asyncio
async def test_categorize_source_social_media(controversy_analyzer: ControversyAnalyzer):
    """Test categorization of a social media source."""
    url = "http://twitter.com/user1/status1"
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    category = await controversy_analyzer.categorize_source(url)
    assert category == "social_media"


@pytest.mark.asyncio
async def test_categorize_source_regulatory(controversy_analyzer: ControversyAnalyzer):
    """Test categorization of a regulatory source."""
    url = "http://sec.gov/document1"
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    category = await controversy_analyzer.categorize_source(url)
    assert category == "regulatory"


@pytest.mark.asyncio
async def test_categorize_source_academic(controversy_analyzer: ControversyAnalyzer):
    """Test categorization of an academic source."""
    url = "http://edu/document1"
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    category = await controversy_analyzer.categorize_source(url)
    assert category == "academic"


@pytest.mark.asyncio
async def test_categorize_source_other(controversy_analyzer: ControversyAnalyzer):
    """Test categorization of an 'other' source."""
    url = "http://example.com/other1"
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    category = await controversy_analyzer.categorize_source(url)
    assert category == "other"


@pytest.mark.asyncio
async def test_categorize_source_none(controversy_analyzer: ControversyAnalyzer):
    """Test categorization of a None URL."""
    url = None
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    category = await controversy_analyzer.categorize_source(url)
    assert category is None


@pytest.mark.asyncio
async def test_categorize_source_exception(controversy_analyzer: ControversyAnalyzer):
    """Test handling of exceptions during URL categorization."""
    url = "http://example.com/article1"
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.categorize_source.__self__ = controversy_analyzer
    # Simulate an error during URL processing
    with pytest.raises(TypeError):
        await controversy_analyzer.categorize_source(url)


def test_summarize_findings_success(controversy_analyzer: ControversyAnalyzer):
    """Test successful summarization of findings."""
    entity = "TestEntity"
    sources = {
        "news": [{"title": "News 1", "url": "http://reuters.com/article1", "published_date": str(datetime.now().year) + "-01-01", "content": "News content"}],
        "social_media": [{"title": "Tweet 1", "url": "http://twitter.com/user1/status1", "published_date": "2022-01-01", "content": "Tweet content"}],
    }
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.summarize_findings.__self__ = controversy_analyzer
    summary = asyncio.run(controversy_analyzer.summarize_findings(entity, sources))

    assert isinstance(summary, dict)
    assert summary["entity"] == entity
    assert summary["total_sources"] == 2
    assert summary["source_breakdown"]["news"] == 1
    assert summary["source_breakdown"]["social_media"] == 1
    assert len(summary["recent_controversies"]) == 1
    assert len(summary["historical_controversies"]) == 1
    controversy_analyzer.logger.error.assert_not_called()


def test_summarize_findings_exception(controversy_analyzer: ControversyAnalyzer):
    """Test handling of exceptions during findings summarization."""
    entity = "TestEntity"
    sources = {
        "news": [{"title": "News 1", "url": "http://reuters.com/article1", "published_date": "2023-01-01", "content": "News content"}],
        "social_media": [{"title": "Tweet 1", "url": "http://twitter.com/user1/status1", "published_date": "2022-01-01", "content": "Tweet content"}],
    }
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.summarize_findings.__self__ = controversy_analyzer
    # Simulate an error by passing incorrect data type
    sources = "incorrect data type"
    summary = asyncio.run(controversy_analyzer.summarize_findings(entity, sources))

    assert isinstance(summary, dict)
    assert summary["entity"] == entity
    assert "error" in summary
    controversy_analyzer.logger.error.assert_called()


@pytest.mark.asyncio
async def test_analyze_entity_controversies_success(controversy_analyzer: ControversyAnalyzer):
    """Test successful analysis of entity controversies."""
    entity = "TestEntity"
    controversy_analyzer.search_controversies = AsyncMock(return_value=[{"url": "http://example.com", "title": "Example"}])
    controversy_analyzer.analyze_sources = AsyncMock(return_value={"news": [{"url": "http://example.com", "title": "Example"}]})
    controversy_analyzer.summarize_findings = AsyncMock(return_value={"entity": entity, "total_sources": 1})
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.analyze_entity_controversies.__self__ = controversy_analyzer
    summary = await controversy_analyzer.analyze_entity_controversies(entity)

    assert isinstance(summary, dict)
    assert summary["entity"] == entity
    assert summary["total_sources"] == 1
    controversy_analyzer.logger.info.assert_called()


@pytest.mark.asyncio
async def test_analyze_entity_controversies_exception(controversy_analyzer: ControversyAnalyzer):
    """Test handling of exceptions during entity controversy analysis."""
    entity = "TestEntity"
    controversy_analyzer.search_controversies = AsyncMock(side_effect=Exception("Test Exception"))
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.analyze_entity_controversies.__self__ = controversy_analyzer
    summary = await controversy_analyzer.analyze_entity_controversies(entity)

    assert isinstance(summary, dict)
    assert summary["entity"] == entity
    assert "error" in summary
    controversy_analyzer.logger.error.assert_called()


def test_run_success(controversy_analyzer: ControversyAnalyzer, monkeypatch: pytest.MonkeyPatch):
    """Test successful execution of the run method."""
    entity = "TestEntity"
    mock_args = MagicMock()
    mock_args.entity = entity
    mock_args.lookback_days = 365
    controversy_analyzer.analyze_entity_controversies = AsyncMock(return_value={"entity": entity, "recent_controversies": []})
    controversy_analyzer.logger = MagicMock()
    controversy_analyzer.run.__self__ = controversy_analyzer

    # Patch asyncio.run to avoid actual async execution during the test
    async def mock_asyncio_run(coro):
        return await coro

    monkeypatch.setattr(asyncio, "run", mock_asyncio_run)

    result = controversy_analyzer.run(mock_args)

    assert isinstance(result, dict)
    assert result["entity"] == entity
    controversy_analyzer.logger.info.assert_called()


def test_main(monkeypatch: pytest.MonkeyPatch):
    """Test the main function."""
    # Mock the ControversyAnalyzer and its run method
    mock_analyzer = MagicMock()
    mock_analyzer_instance = MagicMock()
    mock_analyzer.return_value = mock_analyzer_instance
    mock_analyzer_instance.run.return_value = {"result": "success"}

    # Patch the ControversyAnalyzer class to return the mock
    monkeypatch.setattr("dewey.core.research.analysis.controversy_analyzer.ControversyAnalyzer", mock_analyzer)

    # Mock the command-line arguments
    mock_args = MagicMock()
    mock_args.entity = "TestEntity"
    mock_args.lookback_days = 365

    # Patch the argparse.ArgumentParser.parse_args method to return the mock arguments
    monkeypatch.setattr("argparse.ArgumentParser.parse_args", MagicMock(return_value=mock_args))

    # Call the main function
from dewey.core.research.analysis.controversy_analyzer import main
    main()

    # Assert that the ControversyAnalyzer was instantiated and its run method was called
    mock_analyzer.assert_called_once()
    mock_analyzer_instance.run.assert_called_once_with(mock_args)
