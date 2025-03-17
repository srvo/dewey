"""Schema models for the Syzygy app."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import Field, constr
from django.core.exceptions import ValidationError

from email_processing.prioritization.models import Contact, EnrichmentTask
from .base import BaseSchema, create_input_schema

# Input schemas
ContactInputSchema = create_input_schema(Contact)
EnrichmentTaskInputSchema = create_input_schema(EnrichmentTask)


class BulkContactInput(BaseSchema):
    """Input schema for bulk contact operations."""

    contacts: List[ContactInputSchema]


class BulkTaskInput(BaseSchema):
    """Input schema for bulk task operations."""

    tasks: List[EnrichmentTaskInputSchema]


class BulkAction(BaseSchema):
    """Input schema for bulk actions."""

    ids: List[str]
    action: constr(pattern="^(delete|archive|mark_reviewed)$")
    metadata: Optional[Dict[str, Any]] = None


# Response schemas
class BulkContactResponse(BaseSchema):
    """Response schema for bulk contact operations."""

    status: constr(pattern="^(success|partial|error)$")
    message: str
    results: List[Dict[str, Any]]
    success_count: int
    error_count: int


class BulkTaskResponse(BaseSchema):
    """Response schema for bulk task operations."""

    status: constr(pattern="^(success|partial|error)$")
    message: str
    results: List[Dict[str, Any]]
    success_count: int
    error_count: int


class TaskResponse(BaseSchema):
    """Response schema for task operations."""

    status: constr(pattern="^(success|error)$")
    message: str
    task: Optional[EnrichmentTask] = None


class ContactMerge(BaseSchema):
    """Schema for contact merge analysis."""

    primary_contact_id: str
    candidate_contact_id: str
    confidence: float = Field(ge=0, le=1)
    similarity_scores: Dict[str, float]
    differences: Dict[str, Any]
    reason: str
    suggested_action: constr(pattern="^(merge|keep_separate|needs_review)$")
