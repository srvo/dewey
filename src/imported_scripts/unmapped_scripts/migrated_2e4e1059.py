from unittest.mock import AsyncMock, patch

import pytest
from ai_helper import (
    CompletionRequest,
    DeepSeekProvider,
    Function,
    FunctionParameter,
    Message,
    ModelConfig,
    UseCase,
)


@pytest.fixture
def provider():
    return DeepSeekProvider(api_key="test_key")


@pytest.fixture
def mock_response():
    return {
        "id": "test_id",
        "choices": [{"message": {"role": "assistant", "content": "Test response"}}],
    }


@pytest.mark.asyncio
async def test_complete(provider, mock_response) -> None:
    """Test basic completion."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.status_code = 200

        request = CompletionRequest(
            messages=[Message(role="user", content="Hello")],
            config=ModelConfig(model="deepseek-chat", use_case=UseCase.BALANCED),
        )

        response = await provider.complete(request)
        assert response.choices[0]["message"]["content"] == "Test response"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_function_calling(provider) -> None:
    """Test function calling capability."""
    mock_response = {
        "id": "test_id",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": "get_stock_price",
                        "arguments": '{"symbol": "AAPL"}',
                    },
                },
            },
        ],
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.status_code = 200

        request = CompletionRequest(
            messages=[Message(role="user", content="What's Apple's stock price?")],
            config=ModelConfig(model="deepseek-chat", use_case=UseCase.PRECISE),
            functions=[
                Function(
                    name="get_stock_price",
                    description="Get current stock price",
                    parameters=[
                        FunctionParameter(
                            name="symbol",
                            description="Stock symbol",
                            type="string",
                            required=True,
                        ),
                    ],
                ),
            ],
        )

        response = await provider.complete(request)
        assert (
            response.choices[0]["message"]["function_call"]["name"] == "get_stock_price"
        )
        assert "AAPL" in response.choices[0]["message"]["function_call"]["arguments"]


@pytest.mark.asyncio
async def test_streaming(provider) -> None:
    """Test streaming completion."""
    mock_chunks = [
        {
            "id": "test_id",
            "choices": [{"delta": {"role": "assistant", "content": "Hello"}}],
        },
        {"id": "test_id", "choices": [{"delta": {"content": " world"}}]},
    ]

    with patch("httpx.AsyncClient.stream", new_callable=AsyncMock) as mock_stream:
        mock_stream.return_value.__aenter__.return_value.aiter_lines.return_value = [
            "data: " + str(chunk) for chunk in mock_chunks
        ]

        request = CompletionRequest(
            messages=[Message(role="user", content="Say hello")],
            config=ModelConfig(model="deepseek-chat", use_case=UseCase.CREATIVE),
        )

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
        assert chunks[1]["choices"][0]["delta"]["content"] == " world"
