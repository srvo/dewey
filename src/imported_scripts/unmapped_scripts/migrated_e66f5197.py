"""Integration tests for external API dependencies."""

import logging

import aiohttp
import httpx
import pytest
from prefect import flow, task


# Mock API Response class for testing
class MockResponse:
    def __init__(self, status_code: int, json_data: dict) -> None:
        self.status_code = status_code
        self._json_data = json_data

    async def json(self):
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            msg = "Mock API error"
            raise httpx.HTTPStatusError(
                msg,
                request=httpx.Request("GET", "http://mock"),
                response=self,
            )


# Example API task
@task(retries=2, persist_result=False)
async def fetch_company_data(company_name: str) -> dict:
    """Fetch company data from external API."""
    url = f"http://api.example.com/companies/{company_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return await response.json()


# Example flow using API
@flow
async def analyze_company(company_name: str):
    """Analyze company using external APIs."""
    return await fetch_company_data(company_name)


# API Mock Tests
@pytest.mark.asyncio
async def test_successful_api_call(mock_httpx_client) -> None:
    """Test successful API call."""
    mock_data = {"name": "Test Company", "sector": "Technology", "employees": 1000}
    mock_httpx_client["get"].return_value = MockResponse(200, mock_data)

    result = await analyze_company("test-company")
    assert result == mock_data
    mock_httpx_client["get"].assert_called_once_with(
        "http://api.example.com/companies/test-company",
    )


@pytest.mark.asyncio
async def test_api_error_handling(mock_httpx_client) -> None:
    """Test API error handling."""
    mock_httpx_client["get"].return_value = MockResponse(
        404,
        {"error": "Company not found"},
    )

    with pytest.raises(httpx.HTTPStatusError):
        await analyze_company("nonexistent-company")


# SearXNG Integration Tests
@task(persist_result=False)
async def search_company_news(company: str) -> list:
    """Search for company news using SearXNG."""
    base_url = "http://localhost:8080/search"  # Use localhost for testing
    params = {"q": f"{company} news", "format": "json"}

    session = aiohttp.ClientSession()
    try:
        response = await session.get(base_url, params=params)
        data = await response.json()
        return data["results"]
    finally:
        await session.close()


@flow
async def company_news_flow(company: str):
    """Flow to fetch company news."""
    return await search_company_news(company)


@pytest.mark.asyncio
async def test_searxng_integration(mock_aiohttp_session) -> None:
    """Test SearXNG integration."""
    mock_results = [
        {
            "title": "Test Company News",
            "url": "http://example.com/news",
            "content": "Test content",
        },
    ]
    mock_aiohttp_session.set_response(
        "http://localhost:8080/search",
        {"results": mock_results},
    )

    results = await company_news_flow("test company")
    assert results == mock_results


# OpenAI Integration Tests
@task(persist_result=False)
async def analyze_sentiment(text: str, openai_client) -> str:
    """Analyze text sentiment using OpenAI."""
    response = await openai_client.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "Analyze the sentiment of the following text.",
            },
            {"role": "user", "content": text},
        ],
    )
    return response["choices"][0]["message"]["content"]


@flow
async def sentiment_analysis_flow(text: str, openai_client):
    """Flow to analyze text sentiment."""
    return await analyze_sentiment(text, openai_client)


@pytest.mark.asyncio
async def test_openai_integration(mock_openai) -> None:
    """Test OpenAI integration."""
    mock_openai.add_response(
        "gpt-4",
        {"choices": [{"message": {"content": "Positive sentiment"}}]},
    )

    result = await sentiment_analysis_flow(
        "Great product, highly recommended!",
        mock_openai,
    )
    assert result == "Positive sentiment"
    assert len(mock_openai.calls) == 1
    assert mock_openai.calls[0][1] == "gpt-4"  # Check model


# Database Integration Tests
@task(persist_result=False)
async def store_analysis(company: str, sentiment: str, db) -> None:
    """Store analysis results in database."""
    query = """
    INSERT INTO company_analysis (company, sentiment)
    VALUES ($1, $2)
    """
    await db.execute(query, company, sentiment)


@flow
async def analyze_and_store(company: str, text: str, openai_client, db):
    """Flow to analyze and store results."""
    sentiment = await analyze_sentiment(text, openai_client)
    await store_analysis(company, sentiment, db)
    return sentiment


@pytest.mark.asyncio
async def test_database_integration(mock_openai, mock_database) -> None:
    """Test database integration."""
    mock_openai.add_response(
        "gpt-4",
        {"choices": [{"message": {"content": "Positive sentiment"}}]},
    )

    result = await analyze_and_store(
        "Test Company",
        "Great results this quarter!",
        mock_openai,
        mock_database,
    )

    assert result == "Positive sentiment"
    assert len(mock_database.queries) == 1
    query, args, _ = mock_database.queries[0]
    assert "INSERT INTO company_analysis" in query
    assert args == ("Test Company", "Positive sentiment")


# Controversy Detection Tests
@task(persist_result=False)
async def search_controversies(company: str, searxng_session) -> list:
    """Search for company controversies using SearXNG."""
    base_url = "http://localhost:8080/search"
    params = {
        "q": f"{company} controversy scandal investigation",
        "format": "json",
        "time_range": "year",
    }

    try:
        response = await searxng_session.get(base_url, params=params)
        data = await response.json()
        return data["results"]
    except Exception as e:
        logging.exception(f"Error searching controversies: {e}")
        return []


@task(persist_result=False)
async def analyze_controversy(text: str, openai_client) -> dict:
    """Analyze controversy severity and impact using OpenAI."""
    response = await openai_client.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "Analyze the following controversy text and rate its severity (1-5) and potential impact on the company.",
            },
            {"role": "user", "content": text},
        ],
    )
    return {
        "analysis": response["choices"][0]["message"]["content"],
        "severity": int(response["choices"][0]["message"]["content"].split()[0]),
    }


@flow
async def detect_controversies(company: str, searxng_session, openai_client):
    """Flow to detect and analyze company controversies."""
    controversies = await search_controversies(company, searxng_session)
    if not controversies:
        return {"status": "no_controversies", "details": []}

    analyses = []
    for controversy in controversies[:3]:  # Analyze top 3 controversies
        analysis = await analyze_controversy(controversy["snippet"], openai_client)
        analyses.append(
            {
                "title": controversy["title"],
                "url": controversy["url"],
                "analysis": analysis,
            },
        )

    return {
        "status": "found_controversies",
        "details": sorted(
            analyses,
            key=lambda x: x["analysis"]["severity"],
            reverse=True,
        ),
    }


@pytest.mark.asyncio
async def test_controversy_detection(mock_aiohttp_session, mock_openai) -> None:
    """Test controversy detection flow."""
    # Mock SearXNG response
    mock_controversies = [
        {
            "title": "Test Company Major Scandal",
            "url": "http://example.com/scandal",
            "snippet": "Test Company involved in major controversy...",
        },
        {
            "title": "Minor Investigation",
            "url": "http://example.com/minor",
            "snippet": "Minor regulatory investigation...",
        },
    ]
    mock_aiohttp_session.set_response(
        "http://localhost:8080/search",
        {"results": mock_controversies},
    )

    # Mock OpenAI responses
    mock_openai.add_response(
        "gpt-4",
        {
            "choices": [
                {
                    "message": {
                        "content": "4 - Major controversy with significant reputational impact",
                    },
                },
            ],
        },
    )

    result = await detect_controversies(
        "Test Company",
        mock_aiohttp_session,
        mock_openai,
    )

    assert result["status"] == "found_controversies"
    assert len(result["details"]) > 0
    assert result["details"][0]["analysis"]["severity"] == 4
    assert "reputational impact" in result["details"][0]["analysis"]["analysis"]


@pytest.mark.asyncio
async def test_no_controversies(mock_aiohttp_session, mock_openai) -> None:
    """Test when no controversies are found."""
    mock_aiohttp_session.set_response("http://localhost:8080/search", {"results": []})

    result = await detect_controversies(
        "Clean Company",
        mock_aiohttp_session,
        mock_openai,
    )

    assert result["status"] == "no_controversies"
    assert len(result["details"]) == 0
