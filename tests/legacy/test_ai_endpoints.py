
# Refactored from: test_ai_endpoints
# Date: 2025-03-16T16:19:08.220718
# Refactor Version: 1.0
"""Tests for AI agent endpoints."""

import uuid
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import AsyncClient
from ninja.security import HttpBearer
from syzygy.schemas.ai import (
    ActionType,
    CodeReviewRequest,
    EntityType,
    FallacyRequest,
    Priority,
    TriageRequest,
)

User = get_user_model()


class TestAuth(HttpBearer):
    """Custom authentication for testing."""

    async def authenticate(self, request, token):
        if hasattr(request, "user"):
            return request.user
        return None


@pytest.fixture
@pytest.mark.django_db(transaction=True)
async def authenticated_client():
    """Create an authenticated test client."""
    client = AsyncClient()

    # Create a test user
    unique_id = uuid.uuid4().hex[:8]
    user = await sync_to_async(User.objects.create)(
        email=f"test_{unique_id}@example.com",
        password="testpass123",
        is_staff=True,
        is_active=True,
    )

    # Set the user directly on the client
    client.user = user
    client.headers = {"Authorization": "Bearer test-token"}

    return client


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_triage_endpoint(authenticated_client) -> None:
    """Test triage endpoint."""
    client = await authenticated_client
    payload = TriageRequest(
        content="This is a test message",
        entity_type=EntityType.EMAIL,
        priority=Priority.HIGH,
        action_type=ActionType.ANALYZE_EMAIL,
    ).model_dump()

    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = {"message": "Test response"}
        response = await client.post(
            "/api/syzygy/ai/triage/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "result" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_fallacy_endpoint(authenticated_client) -> None:
    """Test the fallacy analysis endpoint."""
    client = await authenticated_client
    payload = FallacyRequest(
        text="Since most successful people wake up early, waking up early must be the key to success.",
        focus_areas=["causation", "correlation"],
    ).model_dump()

    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = {"message": "Test response"}
        response = await client.post(
            "/api/syzygy/ai/fallacy/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "analysis" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_code_review_endpoint(authenticated_client) -> None:
    """Test the code review endpoint."""
    client = await authenticated_client
    payload = CodeReviewRequest(
        code="""
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)
        """,
        focus_areas=["performance", "readability"],
    ).model_dump()

    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = {"message": "Test response"}
        response = await client.post(
            "/api/syzygy/ai/code-review/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "review" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_triage_error_handling(authenticated_client) -> None:
    """Test error handling in triage endpoint."""
    client = await authenticated_client
    payload = {"content": "This is a test message"}  # Missing required fields
    response = await client.post(
        "/api/syzygy/ai/triage/",
        payload,
        content_type="application/json",
        headers=client.headers,
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_fallacy_error_handling(authenticated_client) -> None:
    """Test error handling in fallacy endpoint."""
    client = await authenticated_client
    payload = {}  # Missing required fields
    response = await client.post(
        "/api/syzygy/ai/fallacy/",
        payload,
        content_type="application/json",
        headers=client.headers,
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_code_review_error_handling(authenticated_client) -> None:
    """Test error handling in code review endpoint."""
    client = await authenticated_client
    payload = {"focus_areas": ["performance"]}  # Missing required code field
    response = await client.post(
        "/api/syzygy/ai/code-review/",
        payload,
        content_type="application/json",
        headers=client.headers,
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_triage_with_all_options(authenticated_client) -> None:
    """Test triage endpoint with all optional parameters."""
    client = await authenticated_client
    payload = TriageRequest(
        content="This is a test message",
        entity_type=EntityType.EMAIL,
        priority=Priority.HIGH,
        action_type=ActionType.ANALYZE_EMAIL,
        context={"previous_messages": ["Hello", "Hi there"]},
        metadata={"sender": "test@example.com", "subject": "Test"},
    ).model_dump()

    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = {"message": "Test response"}
        response = await client.post(
            "/api/syzygy/ai/triage/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "result" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_fallacy_with_context(authenticated_client) -> None:
    """Test fallacy analysis with detailed context."""
    client = await authenticated_client
    payload = FallacyRequest(
        text="Since most successful people wake up early, waking up early must be the key to success.",
        context="Discussion about productivity habits and success factors",
        focus_areas=["causation", "correlation", "generalization"],
    ).model_dump()

    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = {"message": "Test response"}
        response = await client.post(
            "/api/syzygy/ai/fallacy/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "analysis" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_code_review_complex(authenticated_client) -> None:
    """Test code review with complex code and specific focus areas."""
    client = await authenticated_client
    payload = CodeReviewRequest(
        code="""
class DataProcessor:
    def __init__(self):
        self.data = []

    def process_item(self, item):
        try:
            result = item * 2
            self.data.append(result)
            return result
        except:
            print("Error processing item")
            return None

    def get_results(self):
        return self.data
        """,
        focus_areas=["error_handling", "logging", "type_safety", "documentation"],
        context="Production data processing class",
        language="python",
    ).model_dump()

    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = {"message": "Test response"}
        response = await client.post(
            "/api/syzygy/ai/code-review/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "review" in response.json()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_ai_run(authenticated_client) -> None:
    """Test the AI run endpoint."""
    client = await authenticated_client
    with patch("syzygy.ai.base.SyzygyAgent.run") as mock_run:
        mock_run.return_value = "Test response"
        payload = {"prompt": "Test prompt"}
        response = await client.post(
            "/api/syzygy/ai/run/",
            payload,
            content_type="application/json",
            headers=client.headers,
        )
        assert response.status_code == 200
        assert "response" in response.json()
