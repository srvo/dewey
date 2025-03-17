
# Refactored from: test_ai_helper
# Date: 2025-03-16T16:19:11.743055
# Refactor Version: 1.0
import pytest
from ai_helper import (
    CompletionRequest,
    CompletionResponse,
    Function,
    FunctionParameter,
    Message,
    ModelConfig,
    UseCase,
)
from pydantic import ValidationError


def test_use_case_temperatures() -> None:
    """Test that use cases have correct temperature settings."""
    assert UseCase.CREATIVE.get_temperature() == 0.7
    assert UseCase.BALANCED.get_temperature() == 0.5
    assert UseCase.PRECISE.get_temperature() == 0.2


def test_model_config() -> None:
    """Test ModelConfig initialization and temperature setting."""
    config = ModelConfig(model="deepseek-chat", use_case=UseCase.CREATIVE)
    assert config.temperature == UseCase.CREATIVE.get_temperature()
    assert config.model == "deepseek-chat"


def test_message() -> None:
    """Test Message model validation."""
    # Valid message
    message = Message(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"

    # Invalid role
    with pytest.raises(ValidationError):
        Message(role="invalid", content="Hello")


def test_function_parameter() -> None:
    """Test FunctionParameter model."""
    param = FunctionParameter(
        name="symbol",
        description="Stock symbol",
        type="string",
        required=True,
    )
    assert param.name == "symbol"
    assert param.required is True


def test_function() -> None:
    """Test Function model."""
    function = Function(
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
    )
    assert function.name == "get_stock_price"
    assert len(function.parameters) == 1


def test_completion_request() -> None:
    """Test CompletionRequest model."""
    request = CompletionRequest(
        messages=[Message(role="user", content="Hello")],
        config=ModelConfig(model="deepseek-chat", use_case=UseCase.BALANCED),
    )
    assert len(request.messages) == 1
    assert request.config.model == "deepseek-chat"
    assert request.config.temperature == UseCase.BALANCED.get_temperature()


def test_completion_response() -> None:
    """Test CompletionResponse parsing."""
    response = CompletionResponse(
        id="test_id",
        choices=[{"message": {"role": "assistant", "content": "Test response"}}],
    )
    assert response.id == "test_id"
    assert response.choices[0]["message"]["content"] == "Test response"


def test_model_config_custom_temperature() -> None:
    """Test ModelConfig with custom temperature override."""
    custom_temp = 0.9
    config = ModelConfig(
        model="deepseek-chat",
        use_case=UseCase.CREATIVE,
        temperature=custom_temp,
    )
    assert config.temperature == custom_temp
    assert config.use_beta is False


def test_model_config_beta() -> None:
    """Test ModelConfig beta flag."""
    config = ModelConfig(
        model="deepseek-chat",
        use_case=UseCase.BALANCED,
        use_beta=True,
    )
    assert config.use_beta is True


def test_message_with_function_call() -> None:
    """Test Message model with function call."""
    function_call = {"name": "get_stock_price", "arguments": '{"symbol": "AAPL"}'}
    message = Message(role="assistant", content=None, function_call=function_call)
    assert message.function_call == function_call


def test_completion_request_with_functions() -> None:
    """Test CompletionRequest with functions."""
    function = Function(
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
    )
    request = CompletionRequest(
        messages=[Message(role="user", content="Get AAPL price")],
        config=ModelConfig(model="deepseek-chat", use_case=UseCase.BALANCED),
        functions=[function],
        cache_id="test-cache",
    )
    assert len(request.functions) == 1
    assert request.cache_id == "test-cache"


def test_completion_response_with_cache_hit() -> None:
    """Test CompletionResponse with cache hit."""
    response = CompletionResponse(
        id="test_id",
        choices=[{"message": {"role": "assistant", "content": "Test response"}}],
        cache_hit=True,
    )
    assert response.cache_hit is True
