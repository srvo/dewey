from unittest.mock import AsyncMock, patch

import pytest
from ai_helper import AIClient, Message, ModelConfig, ModelProvider, UseCase


@pytest.fixture
def client():
    return AIClient(api_key="test_key", provider=ModelProvider.DEEPSEEK)


@pytest.fixture
def mock_response():
    return {
        "id": "test_id",
        "choices": [{"message": {"role": "assistant", "content": "Test response"}}],
    }


@pytest.mark.asyncio
async def test_client_initialization(client) -> None:
    """Test client initialization with config."""
    assert client.api_key == "test_key"
    assert client.provider == ModelProvider.DEEPSEEK


@pytest.mark.asyncio
async def test_client_completion(client, mock_response) -> None:
    """Test client completion request."""
    with patch(
        "ai_helper.providers.DeepSeekProvider.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.return_value = mock_response

        response = await client.complete(
            messages=[Message(role="user", content="Hello")],
            config=ModelConfig(model="deepseek-chat", use_case=UseCase.BALANCED),
        )

        assert response == mock_response
        mock_complete.assert_called_once()


@pytest.mark.asyncio
async def test_client_streaming(client) -> None:
    """Test client streaming completion."""
    mock_chunks = [
        {
            "id": "test_id",
            "choices": [{"delta": {"role": "assistant", "content": "Hello"}}],
        },
        {"id": "test_id", "choices": [{"delta": {"content": " world"}}]},
    ]

    with patch(
        "ai_helper.providers.DeepSeekProvider.complete_stream",
        new_callable=AsyncMock,
    ) as mock_stream:
        mock_stream.return_value.__aiter__.return_value = mock_chunks

        chunks = []
        async for chunk in client.complete_stream(
            messages=[Message(role="user", content="Say hello")],
            config=ModelConfig(model="deepseek-chat", use_case=UseCase.CREATIVE),
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
        assert chunks[1]["choices"][0]["delta"]["content"] == " world"


@pytest.mark.asyncio
async def test_client_error_handling(client) -> None:
    """Test client error handling."""
    with patch(
        "ai_helper.providers.DeepSeekProvider.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            await client.complete(
                messages=[Message(role="user", content="Hello")],
                config=ModelConfig(model="deepseek-chat", use_case=UseCase.BALANCED),
            )

        assert str(exc_info.value) == "API Error"
