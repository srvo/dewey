from enum import Enum
from typing import Optional, List, Dict, Any
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
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class FallacyRequest(Schema):
    text: str
    context: Optional[str] = None
    focus_areas: Optional[List[str]] = None


class CodeReviewRequest(Schema):
    code: str
    focus_areas: List[str]
    context: Optional[str] = None
    language: Optional[str] = "python"


class AIRunRequest(Schema):
    prompt: str


# Response Models
class TriageResponse(Schema):
    result: Dict[str, Any]


class FallacyResponse(Schema):
    analysis: Dict[str, Any]


class CodeReviewResponse(Schema):
    review: Dict[str, Any]


class AIRunResponse(Schema):
    response: str
