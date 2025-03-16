import pytest
import pytest_asyncio
from ai_helper.client import AIClient
from ai_helper.models import Message, ModelProvider, UseCase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = "sk-7f08292f2fd341c9912ea8ef47a2f188"


@pytest_asyncio.fixture
async def client():
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")
    client = AIClient.create(provider=ModelProvider.DEEPSEEK, api_key=api_key)
    try:
        yield client
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_code_analysis(client) -> None:
    """Test code analysis capability with real API."""
    code = """
    def process_data(data):
        results = []
        for item in data:
            if isinstance(item, dict):
                results.append(item.get('value', 0))
            elif isinstance(item, (int, float)):
                results.append(item)
        return sum(results)
    """

    messages = [
        Message(
            role="user",
            content=f"Analyze this code for potential improvements and edge cases:\n{code}",
        ),
    ]

    response = await client.complete(
        messages=messages,
        model="deepseek-chat",
        use_case=UseCase.CODE_ANALYSIS,
    )

    assert response.content
    assert (
        "improvement" in response.content.lower()
        or "edge case" in response.content.lower()
    )


@pytest.mark.asyncio
async def test_function_calling(client) -> None:
    """Test function calling with real API."""
    messages = [
        Message(
            role="user",
            content="The temperature today is 72°F with 45% humidity.",
        ),
    ]

    response = await client.complete(
        messages=messages,
        model="deepseek-chat",
        use_case=UseCase.FUNCTION_CALLING,
        functions=[
            {
                "name": "extract_data_points",
                "description": "Extract numerical values from text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number"},
                        "humidity": {"type": "number"},
                    },
                },
            },
        ],
    )

    # Check that the response contains the extracted values
    assert response.content is not None
    assert "72°F" in response.content
    assert "45%" in response.content


@pytest.mark.asyncio
async def test_multi_step_reasoning(client) -> None:
    """Test multi-step reasoning with real API."""
    messages = [
        Message(
            role="user",
            content="Let's solve this step by step: A company's revenue grew by 15% in 2021 and 25% in 2022. If their revenue in 2020 was $1M, what was their revenue in 2022?",
        ),
    ]

    response = await client.complete(
        messages=messages,
        model="deepseek-chat",
        use_case=UseCase.ANALYSIS,
    )

    assert response.content
    assert "1.15" in response.content or "15%" in response.content
    assert "1.25" in response.content or "25%" in response.content
    assert any(x in response.content for x in ["1,437,500", "1.4375", "1437500"])
