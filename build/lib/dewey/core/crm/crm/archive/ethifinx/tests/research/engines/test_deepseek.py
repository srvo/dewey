"""
Tests for the DeepSeek Analysis Engine.

Tests both the base engine functionality inheritance and DeepSeek-specific features.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json
from typing import List, Dict, Any

from ethifinx.research.engines.deepseek import (
    DeepSeekEngine,
    SearchResult,
    ConversationMessage,
    APIResponse,
    ChatOptions,
    FunctionCall
)


@pytest.fixture
def mock_api_response() -> Dict[str, Any]:
    """Mock API response fixture."""
    return {
        "choices": [{
            "message": {
                "content": "Test analysis content",
                "role": "assistant"
            }
        }],
        "usage": {
            "prompt_cache_hit_tokens": 10,
            "prompt_cache_miss_tokens": 5,
            "total_tokens": 15
        }
    }


@pytest.fixture
def engine() -> DeepSeekEngine:
    """Create a DeepSeek engine instance."""
    return DeepSeekEngine(api_key="test_key")


@pytest.fixture
def search_results() -> List[Dict[str, Any]]:
    """Sample search results fixture."""
    return [
        {
            "title": "Test Company Ethics Report",
            "snippet": "Environmental violations found in 2023",
            "url": "http://test.com/report",
            "timestamp": "2023-12-01T00:00:00Z"
        },
        {
            "title": "Labor Issues Investigation",
            "snippet": "Multiple labor rights concerns identified",
            "url": "http://test.com/labor",
            "timestamp": "2023-11-01T00:00:00Z"
        }
    ]


class TestDeepSeekEngineBase:
    """Test base AnalysisEngine functionality."""

    async def test_analyze_inheritance(
        self,
        engine: DeepSeekEngine,
        search_results: List[Dict[str, Any]],
        mock_api_response: Dict[str, Any]
    ):
        """Test that analyze method properly implements base class contract."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_api_response
            
            result = await engine.analyze(search_results)
            
            # Check required fields from base class
            assert "content" in result
            assert "source" in result
            assert "timestamp" in result
            assert isinstance(result["content"], str)
            assert result["source"] == "deepseek"
            assert isinstance(result["timestamp"], str)

    async def test_error_handling_inheritance(
        self,
        engine: DeepSeekEngine,
        search_results: List[Dict[str, Any]]
    ):
        """Test error handling follows base class patterns."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API Error")
            
            result = await engine.analyze(search_results)
            
            # Check error handling format
            assert "error" in result
            assert result["error"] == "API Error"
            assert result["source"] == "deepseek"
            assert isinstance(result["timestamp"], str)


class TestDeepSeekEngineSpecific:
    """Test DeepSeek-specific functionality."""

    async def test_chat_completion(
        self,
        engine: DeepSeekEngine,
        mock_api_response: Dict[str, Any]
    ):
        """Test basic chat completion."""
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_api_response
            
            response = await engine.chat_completion(messages)
            
            assert response["content"] == "Test analysis content"
            assert response["cache_metrics"]["hit_tokens"] == 10
            assert response["cache_metrics"]["miss_tokens"] == 5
            assert not response["error"]

    async def test_json_completion(
        self,
        engine: DeepSeekEngine,
        mock_api_response: Dict[str, Any]
    ):
        """Test JSON mode completion."""
        messages = [{"role": "user", "content": "List colors"}]
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_api_response
            
            response = await engine.json_completion(messages)
            
            # Verify JSON mode request
            called_args = mock_post.call_args[1]["json"]
            assert called_args["response_format"] == {"type": "json_object"}

    async def test_function_calling(
        self,
        engine: DeepSeekEngine
    ):
        """Test function registration and calling."""
        # Register test function
        engine.register_function(
            name="test_func",
            description="Test function",
            parameters={"type": "object", "properties": {}},
            handler=AsyncMock()
        )
        
        # Verify registration
        funcs = engine.get_function_definitions()
        assert len(funcs) == 1
        assert funcs[0]["name"] == "test_func"
        
        # Test function call handling
        func_call = {"name": "test_func", "arguments": "{}"}
        await engine.handle_function_call(func_call)
        
        # Verify rate limiting
        with pytest.raises(ValueError, match="rate limit exceeded"):
            for _ in range(61):  # Default rate limit is 60
                await engine.handle_function_call(func_call)

    async def test_chat_prefix_completion(
        self,
        engine: DeepSeekEngine,
        mock_api_response: Dict[str, Any]
    ):
        """Test chat prefix completion (Beta)."""
        messages = [
            {"role": "user", "content": "Write code"},
            {"role": "assistant", "content": "```python\n", "prefix": True}
        ]
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_api_response
            
            response = await engine.chat_prefix_completion(
                messages,
                stop=["```"]
            )
            
            # Verify beta URL and stop sequence
            assert mock_post.call_args[0][0].startswith("https://api.deepseek.com/beta")
            assert mock_post.call_args[1]["json"]["stop"] == ["```"]

    def test_template_management(self, engine: DeepSeekEngine):
        """Test conversation template management."""
        template = [
            {"role": "system", "content": "You are a test assistant"}
        ]
        
        # Test adding template
        engine.add_template("test", template)
        assert "test" in engine.conversation_templates
        
        # Test retrieving template
        retrieved = engine.get_template("test")
        assert retrieved == template
        
        # Test non-existent template
        assert engine.get_template("nonexistent") == []

    async def test_cache_metrics(
        self,
        engine: DeepSeekEngine,
        mock_api_response: Dict[str, Any]
    ):
        """Test cache metrics tracking."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_api_response
            
            await engine.chat_completion([{"role": "user", "content": "Test"}])
            
            assert engine.cache_metrics.prompt_cache_hit_tokens == 10
            assert engine.cache_metrics.prompt_cache_miss_tokens == 5
            assert engine.cache_metrics.total_requests == 1

    async def test_error_analysis(
        self,
        engine: DeepSeekEngine,
        mock_api_response: Dict[str, Any]
    ):
        """Test error analysis functionality."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            # First call raises error, second call (error analysis) succeeds
            mock_post.side_effect = [
                Exception("Test Error"),
                AsyncMock(
                    status_code=200,
                    json=Mock(return_value=mock_api_response)
                )
            ]
            
            response = await engine.chat_completion(
                [{"role": "user", "content": "Test"}]
            )
            
            assert response["error"] == "Test Error"
            assert mock_post.call_count == 2  # Original call + error analysis 