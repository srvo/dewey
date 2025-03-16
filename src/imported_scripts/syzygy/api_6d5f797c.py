"""API endpoints for Syzygy app."""

from django.http import HttpRequest
from ninja import NinjaAPI, Router
from ninja.security import HttpBearer

from .ai.base import SyzygyAgent
from .schemas.ai import (
    AIRunRequest,
    AIRunResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    FallacyRequest,
    FallacyResponse,
    TriageRequest,
    TriageResponse,
)


class TestAuth(HttpBearer):
    """Custom authentication for testing."""

    async def authenticate(self, request, token):
        if hasattr(request, "user"):
            return request.user
        return None


# Initialize API with authentication
api = NinjaAPI(
    auth=TestAuth(),
    title="Syzygy API",
    version="1.0.0",
    urls_namespace="syzygy-api",
)

# Create routers
ai_router = Router(tags=["ai"])


@ai_router.post("/triage/", response=TriageResponse)
async def triage_endpoint(request: HttpRequest, data: TriageRequest):
    agent = SyzygyAgent()
    result = await agent.run(data.dict())
    return {"result": result}


@ai_router.post("/fallacy/", response=FallacyResponse)
async def fallacy_endpoint(request: HttpRequest, data: FallacyRequest):
    agent = SyzygyAgent()
    result = await agent.run(data.dict())
    return {"analysis": result}


@ai_router.post("/code-review/", response=CodeReviewResponse)
async def code_review_endpoint(request: HttpRequest, data: CodeReviewRequest):
    agent = SyzygyAgent()
    result = await agent.run(data.dict())
    return {"review": result}


@ai_router.post("/run/", response=AIRunResponse)
async def ai_run_endpoint(request: HttpRequest, data: AIRunRequest):
    agent = SyzygyAgent()
    result = await agent.run(data.dict())
    return {"response": result}


# Register routers
api.add_router("/ai/", ai_router)
