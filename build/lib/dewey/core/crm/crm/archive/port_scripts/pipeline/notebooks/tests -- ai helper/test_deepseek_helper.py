import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from ai_helper.deepseek_helper import DeepSeekFunctionHelper, FunctionMetadata
import os

@pytest.fixture
def mock_openai():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client

@pytest.fixture
def helper():
    """Create a DeepSeek helper instance for testing."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
    # Remove trailing 'n' and any whitespace
    api_key = api_key.strip().rstrip('n')
    return DeepSeekFunctionHelper(api_key=api_key, base_url="https://api.deepseek.com")

@pytest.fixture
def real_api_list():
    """Real API list for testing with actual rate limits."""
    return [
        {
            "name": "tavily_search",
            "description": "Search for information using Tavily's semantic search API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "search_depth": {
                        "type": "string",
                        "description": "basic or deep search",
                        "enum": ["basic", "deep"]
                    }
                },
                "required": ["query"]
            },
            "metadata": {
                "keywords": ["search", "research", "semantic", "ai"],
                "rate_limit": 1000,  # 1000 requests per month
                "priority": 1,
                "api_key": "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"
            }
        },
        {
            "name": "bing_search",
            "description": "Search the web using Bing API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of results to return"
                    }
                },
                "required": ["query"]
            },
            "metadata": {
                "keywords": ["search", "web", "news"],
                "rate_limit": 3,  # 3 TPS
                "priority": 2,
                "api_key": "a16696a75d3445e3a562d8c7779f59a7"
            }
        },
        {
            "name": "brave_search",
            "description": "Search the web using Brave Search API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            },
            "metadata": {
                "keywords": ["search", "privacy", "web"],
                "rate_limit": 1,  # 1 request per second
                "priority": 3,
                "api_key": "BSA6HeFEU01rayFC4ZdpggxfG4YJBhc"
            }
        }
    ]

def test_init(helper):
    """Test initialization of DeepSeekFunctionHelper."""
    assert helper.functions == []
    assert helper.function_call_counts == {}
    assert helper.last_call_time == {}

def test_define_real_api_functions(helper, real_api_list):
    """Test defining real API functions."""
    helper.define_api_functions(real_api_list)
    assert len(helper.functions) == 3
    assert helper.functions[0]["function"]["name"] == "tavily_search"
    assert helper.functions[1]["function"]["name"] == "bing_search"
    assert helper.functions[2]["function"]["name"] == "brave_search"

def test_preprocess_query(helper):
    """Test query preprocessing with real search queries."""
    query = "What are the latest developments in AI technology?"
    processed = helper.preprocess_query(query)
    assert "latest" in processed
    assert "developments" in processed
    assert "ai" in processed
    assert "technology" in processed
    assert "the" not in processed

def test_filter_real_functions(helper, real_api_list):
    """Test function filtering with real API keywords."""
    helper.define_api_functions(real_api_list)
    query_keywords = ["search", "privacy"]
    filtered = helper.filter_functions(query_keywords)
    assert len(filtered) >= 1
    assert any(f["function"]["name"] == "brave_search" for f in filtered)

def test_check_real_rate_limits(helper, real_api_list):
    """Test rate limit checking with real API limits."""
    helper.define_api_functions(real_api_list)
    
    # Test Brave Search rate limit (1 per second)
    assert helper.check_rate_limit("brave_search") == True
    helper.update_function_call_count("brave_search")
    assert helper.check_rate_limit("brave_search") == False
    
    # Test Bing Search rate limit (3 TPS)
    assert helper.check_rate_limit("bing_search") == True
    for _ in range(3):
        helper.update_function_call_count("bing_search")
    assert helper.check_rate_limit("bing_search") == False

def test_score_real_functions(helper, real_api_list):
    """Test function scoring with real APIs."""
    helper.define_api_functions(real_api_list)
    query_keywords = ["search", "privacy", "ai"]
    scored = helper.score_functions(query_keywords)
    
    # Brave should be high in results due to privacy keyword
    assert len(scored) == 3
    assert any(f["function"]["name"] == "brave_search" for f in scored[:2])

@pytest.mark.asyncio
async def test_real_search_query(helper, real_api_list):
    """Test sending a real search query."""
    helper.define_api_functions(real_api_list)
    
    messages = [{"role": "user", "content": "Search for information about artificial intelligence"}]
    
    # Make a real API call
    results = await helper.send_query_with_functions(messages, "artificial intelligence")
    
    # Verify we got some results
    assert results is not None
    
    # If we got a list of results, verify their structure
    if isinstance(results, list):
        for result in results:
            assert isinstance(result, dict)
            if "error" not in result:
                assert "title" in result or "content" in result
    # If we got a message, verify it's properly structured
    else:
        assert "content" in results or "tool_calls" in results

@pytest.mark.asyncio
async def test_real_api_error_handling(helper, real_api_list):
    """Test error handling with real APIs."""
    helper.define_api_functions(real_api_list)
    
    # Test with an invalid API key to trigger an error
    original_api_key = helper.api_key
    helper.api_key = "invalid-key"
    
    messages = [{"role": "user", "content": "Search for AI news"}]
    
    try:
        # Make a real API call that should fail
        results = await helper.send_query_with_functions(messages, "AI news")
        assert False, "Expected an error but got results"
    except Exception as e:
        # Verify we got the expected error
        assert "401" in str(e) or "Unauthorized" in str(e)
    finally:
        # Restore the original API key
        helper.api_key = original_api_key

def test_real_api_rate_limit_tracking(helper, real_api_list):
    """Test rate limit tracking for real APIs."""
    helper.define_api_functions(real_api_list)
    
    # Test Tavily monthly limit
    for _ in range(10):
        helper.update_function_call_count("tavily_search")
    assert helper.function_call_counts["tavily_search"] == 10
    
    # Test Brave Search rate limit
    helper.update_function_call_count("brave_search")
    assert helper.function_call_counts["brave_search"] == 1
    assert helper.check_rate_limit("brave_search") == False  # Should be rate limited for 1 second 

@pytest.mark.asyncio
async def test_company_metrics_analysis(helper, real_api_list):
    """Test company metrics analysis with real API calls."""
    helper.define_api_functions(real_api_list)
    
    # Test analyzing metrics for a real company
    results = await helper.analyze_company_metrics("Duolingo", "CAC and LTV")
    
    # Verify we got results
    assert results is not None
    assert isinstance(results, list)
    
    # If we got results, verify their structure
    if len(results) > 0:
        for result in results:
            assert isinstance(result, dict)
            assert "title" in result
            assert "url" in result
            assert "content" in result
            assert "source" in result
            assert "score" in result
            
            # Verify the content is relevant to either Duolingo or CAC/LTV metrics
            content = result["content"].lower()
            title = result["title"].lower()
            combined_text = content + " " + title
            assert any(term in combined_text for term in [
                "duolingo", "language", "learning", "subscription", "revenue",
                "cac", "ltv", "customer acquisition", "lifetime value"
            ])

@pytest.mark.asyncio
async def test_fetch_api_docs(helper):
    """Test fetching API documentation from real URLs."""
    # Test with a real API documentation URL
    docs_url = "https://api.deepseek.com/docs"
    docs = await helper.fetch_api_docs(docs_url)
    
    # Verify we got some documentation
    assert docs is not None
    assert isinstance(docs, str)
    
    # Test caching
    cached_docs = await helper.fetch_api_docs(docs_url)
    assert cached_docs == docs
    
    # Test with an invalid URL
    invalid_docs = await helper.fetch_api_docs("https://invalid-url-that-doesnt-exist.com/docs")
    assert invalid_docs == ""
    
    # Test with a non-documentation URL
    non_docs = await helper.fetch_api_docs("https://example.com")
    assert isinstance(non_docs, str)  # Should still return a string, even if empty

@pytest.mark.asyncio
async def test_api_error_handling(helper, real_api_list):
    """Test API error handling with real documentation."""
    # Add API docs URLs to the functions
    real_api_list[0]["metadata"]["api_docs_url"] = "https://api.tavily.com/docs"
    helper.define_api_functions(real_api_list)
    
    # Create a test error
    test_error = Exception("API rate limit exceeded")
    
    # Test error handling for Tavily search
    await helper.handle_api_error("tavily_search", test_error)
    
    # Verify that documentation was fetched and cached
    assert any("api.tavily.com" in url for url in helper.api_docs_cache.keys())
    
    # Test error handling with invalid function name
    await helper.handle_api_error("nonexistent_function", test_error)
    
    # Test error handling with missing API docs URL
    modified_api = real_api_list[0].copy()
    del modified_api["metadata"]["api_docs_url"]
    helper.define_api_functions([modified_api])
    await helper.handle_api_error("tavily_search", test_error)
    
    # Test error handling with invalid API docs URL
    modified_api["metadata"]["api_docs_url"] = "https://invalid-url-that-doesnt-exist.com/docs"
    helper.define_api_functions([modified_api])
    await helper.handle_api_error("tavily_search", test_error)
    
    # Verify that the cache still contains the original valid documentation
    assert any("api.tavily.com" in url for url in helper.api_docs_cache.keys())

@pytest.mark.asyncio
async def test_api_integration_with_docs(helper, real_api_list):
    """Test API integration with automatic documentation lookup on error."""
    # Add API docs URLs to all functions
    real_api_list[0]["metadata"]["api_docs_url"] = "https://api.tavily.com/docs"
    helper.define_api_functions(real_api_list)
    
    # Test with invalid API key to trigger error handling
    async def error_handler(args):
        raise Exception("Invalid API key: Key must start with 'Bearer'")
    
    function_handlers = {
        "tavily_search": error_handler
    }
    
    try:
        results = await helper.handle_multiple_functions(
            "Search for AI news",
            [{"role": "user", "content": "Search for AI news"}],
            function_handlers
        )
        assert False, "Expected an error but got results"
    except Exception as e:
        # Verify error was handled and documentation was fetched
        assert "Invalid API key" in str(e)
        assert any("api.tavily.com" in url for url in helper.api_docs_cache.keys()) 