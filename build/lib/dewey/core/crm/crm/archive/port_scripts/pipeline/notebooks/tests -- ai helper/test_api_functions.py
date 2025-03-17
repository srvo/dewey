"""
Test file for API functions.

IMPORTANT: These tests MUST use real API calls. Under NO circumstances should mock API calls be used.
The purpose of these tests is to verify actual API behavior and integration, not simulated responses.

Key points:
1. All API calls must be real
2. No mocking of responses
3. Tests should handle real API latency and rate limits
4. Tests should use actual API keys from environment variables
"""

import pytest
import os
from datetime import datetime
import httpx
import asyncio
from typing import Dict, List, Any, Optional
from ai_helper.deepseek_helper import DeepSeekFunctionHelper, FunctionMetadata
import json

@pytest.fixture
def api_key() -> str:
    """Get the DeepSeek API key from environment variables."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY environment variable not set")
    return api_key

@pytest.fixture
def helper(api_key):
    """Create a DeepSeek helper instance for testing."""
    helper = DeepSeekFunctionHelper(api_key=api_key)
    
    # Define test API functions
    api_list = [
        {
            "name": "deepseek_chat",
            "description": "Chat completion using DeepSeek API",
            "parameters": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["messages"]
            },
            "metadata": {
                "keywords": ["chat", "completion", "llm"],
                "rate_limit": 100,
                "priority": 1,
                "api_docs_url": "https://api.deepseek.com"
            }
        }
    ]
    
    helper.define_api_functions(api_list)
    return helper

@pytest.mark.asyncio
async def test_chained_research(helper: DeepSeekFunctionHelper):
    """Test chained research and analysis using DeepSeek."""
    try:
        initial_query = "Research the impact of AI on financial markets"
        follow_up_questions = [
            "What are the challenges in implementing AI trading systems?",
            "Can you provide examples of successful AI trading implementations?"
        ]
        
        research_results = await helper.conduct_research(
            initial_query=initial_query,
            follow_up_questions=follow_up_questions
        )
        
        assert isinstance(research_results, list)
        assert all(isinstance(result, dict) for result in research_results)
        assert all("content" in result for result in research_results)
        
        formatted_results = helper.format_research_results(
            research_results,
            "AI in Financial Markets - Comprehensive Research"
        )
        
        assert isinstance(formatted_results, list)
        assert len(formatted_results) > 0
        assert "sections" in formatted_results[0]
        
        filepath = helper.write_analysis_to_file(formatted_results, "AI_Trading_Research")
        assert os.path.exists(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
            assert "AI in Financial Markets" in content
        
        os.remove(filepath)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            pytest.skip("Invalid or expired API key")
        raise

@pytest.mark.asyncio
async def test_research_with_docs_lookup(helper: DeepSeekFunctionHelper):
    """Test research process with documentation lookup integration."""
    try:
        query = "Research how to implement automated trading using Alpha Vantage API"
        follow_up_questions = [
            "What are the rate limiting considerations?",
            "What are the best practices for real-time data access?"
        ]
        
        research_results = await helper.research_with_docs(
            query=query,
            api_name="Alpha Vantage",
            follow_up_questions=follow_up_questions
        )
        
        assert isinstance(research_results, list)
        assert all(isinstance(result, dict) for result in research_results)
        assert all("content" in result for result in research_results)
        
        formatted_results = helper.format_research_results(
            research_results,
            "Alpha Vantage API Implementation Guide"
        )
        
        assert isinstance(formatted_results, list)
        assert len(formatted_results) > 0
        assert "sections" in formatted_results[0]
        
        filepath = helper.write_analysis_to_file(formatted_results, "Alpha_Vantage_Implementation_Guide")
        assert os.path.exists(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
            assert "Alpha Vantage API Implementation Guide" in content
        
        os.remove(filepath)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            pytest.skip("Invalid or expired API key")
        raise

@pytest.mark.asyncio
async def test_error_handling(helper: DeepSeekFunctionHelper):
    """Test error handling and recovery mechanisms."""
    # Test with invalid API key
    invalid_helper = DeepSeekFunctionHelper(api_key="invalid_key")
    result = await invalid_helper.conduct_research(
        initial_query="Test query",
        follow_up_questions=[]
    )
    
    # Verify error response
    assert len(result) > 0
    assert "Error" in result[0]["content"]
    assert "401 Unauthorized" in result[0]["content"]
    assert result[0]["source"] == "Error"

@pytest.mark.asyncio
async def test_rate_limiting(helper: DeepSeekFunctionHelper):
    """Test rate limiting behavior."""
    try:
        # Configure rate limit testing
        test_queries = [
            f"Test query {i}" for i in range(5)
        ]
        
        # Execute multiple queries in parallel
        tasks = [
            helper.conduct_research(
                initial_query=query,
                follow_up_questions=["Follow up"]
            )
            for query in test_queries
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        assert len(results) == len(test_queries)
        assert all(isinstance(r, (list, Exception)) for r in results)
        
        # Check rate limiting through function call counts
        for func in helper.functions:
            func_name = func["function"]["name"]
            assert helper.function_call_counts[func_name] <= func["function"]["metadata"]["rate_limit"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            pytest.skip("Invalid or expired API key")
        raise

@pytest.mark.asyncio
async def test_concurrent_api_calls(helper: DeepSeekFunctionHelper):
    """Test concurrent API call handling."""
    try:
        # Test parallel research queries
        queries = [
            "Research AI in healthcare",
            "Research AI in education",
            "Research AI in finance"
        ]
        
        async def research_task(query: str):
            return await helper.conduct_research(
                initial_query=query,
                follow_up_questions=["What are the main challenges?"]
            )
        
        # Execute concurrent research tasks
        tasks = [research_task(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == len(queries)
        assert all(isinstance(result, list) for result in results)
        assert all(len(result) >= 2 for result in results)  # Initial + follow-up
        
        # Check that results contain valid content
        for result in results:
            assert all("content" in r and r["content"] for r in result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            pytest.skip("Invalid or expired API key")
        raise

@pytest.mark.asyncio
async def test_research_result_formatting(helper: DeepSeekFunctionHelper):
    """Test the formatting and processing of research results."""
    try:
        # Conduct test research
        research_results = await helper.conduct_research(
            initial_query="Research data visualization best practices",
            follow_up_questions=["What are the key principles?"]
        )
        
        # Test formatting
        formatted_results = helper.format_research_results(
            research_results,
            "Data Visualization Guide"
        )
        
        assert isinstance(formatted_results, list)
        assert len(formatted_results) > 0
        assert "sections" in formatted_results[0]
        
        # Verify structure
        assert "title" in formatted_results[0]
        assert isinstance(formatted_results[0]["sections"], list)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            pytest.skip("Invalid or expired API key")
        raise 