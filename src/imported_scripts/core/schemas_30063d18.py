from __future__ import annotations

from enum import Enum
from typing import Any

from ninja import Schema


class EntityType(str, Enum):
    EMAIL = "email"
    DOCUMENT = "document"
    MESSAGE = "message"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    ANALYZE_EMAIL = "analyze_email"
    REVIEW_CODE = "review_code"
    ANALYZE_FALLACY = "analyze_fallacy"


# Request Models
class TriageRequest(Schema):
    content: str
    entity_type: EntityType
    priority: Priority
    action_type: ActionType
    context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class FallacyRequest(Schema):
    text: str
    context: str | None = None
    focus_areas: list[str] | None = None


class CodeReviewRequest(Schema):
    code: str
    focus_areas: list[str]
    context: str | None = None
    language: str | None = "python"


class AIRunRequest(Schema):
    prompt: str


# Response Models
class TriageResponse(Schema):
    result: dict[str, Any]


class FallacyResponse(Schema):
    analysis: dict[str, Any]


class CodeReviewResponse(Schema):
    review: dict[str, Any]


class AIRunResponse(Schema):
    response: str
