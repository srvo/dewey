import pytest
from ai_helper import (
    AIClient,
    Function,
    FunctionParameter,
    Message,
    ModelConfig,
    ModelProvider,
    UseCase,
)


async def mock_get_stock_price(symbol: str) -> float:
    """Mock function for testing function calling."""
    return 150.0


@pytest.fixture
def client():
    return AIClient(api_key="test_key", provider=ModelProvider.DEEPSEEK)


@pytest.mark.asyncio
async def test_basic_chat(client) -> None:
    """Test basic chat completion."""
    response = await client.complete(
        messages=[Message(role="user", content="Say hello")],
        config=ModelConfig(model="deepseek-chat", use_case=UseCase.BALANCED),
    )
    assert response.id is not None
    assert len(response.choices) > 0
    assert response.choices[0]["message"]["content"] is not None


@pytest.mark.asyncio
async def test_function_calling(client) -> None:
    """Test function calling with real API."""
    messages = [Message(role="user", content="What's the current price of AAPL stock?")]
    functions = [
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
    ]

    response = await client.complete(
        messages=messages,
        config=ModelConfig(model="deepseek-chat", use_case=UseCase.PRECISE),
        functions=functions,
    )

    assert response.id is not None
    assert len(response.choices) > 0
    function_call = response.choices[0]["message"].get("function_call")
    assert function_call is not None
    assert function_call["name"] == "get_stock_price"
    assert "AAPL" in function_call["arguments"]


@pytest.mark.asyncio
async def test_streaming_chat(client) -> None:
    """Test streaming chat completion."""
    chunks = []
    async for chunk in client.complete_stream(
        messages=[Message(role="user", content="Count from 1 to 3")],
        config=ModelConfig(model="deepseek-chat", use_case=UseCase.CREATIVE),
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_response = "".join(
        chunk["choices"][0]["delta"].get("content", "")
        for chunk in chunks
        if "content" in chunk["choices"][0]["delta"]
    )
    assert any(str(i) in full_response for i in range(1, 4))
