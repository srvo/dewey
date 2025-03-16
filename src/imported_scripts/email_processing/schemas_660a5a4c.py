"""Schema models for the Syzygy app."""

from __future__ import annotations

from typing import Any

from email_processing.prioritization.models import Contact, EnrichmentTask
from pydantic import Field, constr

from .base import BaseSchema, create_input_schema

# Input schemas
ContactInputSchema = create_input_schema(Contact)
EnrichmentTaskInputSchema = create_input_schema(EnrichmentTask)


class BulkContactInput(BaseSchema):
    """Input schema for bulk contact operations."""

    contacts: list[ContactInputSchema]


class BulkTaskInput(BaseSchema):
    """Input schema for bulk task operations."""

    tasks: list[EnrichmentTaskInputSchema]


class BulkAction(BaseSchema):
    """Input schema for bulk actions."""

    ids: list[str]
    action: constr(pattern="^(delete|archive|mark_reviewed)$")
    metadata: dict[str, Any] | None = None


# Response schemas
class BulkContactResponse(BaseSchema):
    """Response schema for bulk contact operations."""

    status: constr(pattern="^(success|partial|error)$")
    message: str
    results: list[dict[str, Any]]
    success_count: int
    error_count: int


class BulkTaskResponse(BaseSchema):
    """Response schema for bulk task operations."""

    status: constr(pattern="^(success|partial|error)$")
    message: str
    results: list[dict[str, Any]]
    success_count: int
    error_count: int


class TaskResponse(BaseSchema):
    """Response schema for task operations."""

    status: constr(pattern="^(success|error)$")
    message: str
    task: EnrichmentTask | None = None


class ContactMerge(BaseSchema):
    """Schema for contact merge analysis."""

    primary_contact_id: str
    candidate_contact_id: str
    confidence: float = Field(ge=0, le=1)
    similarity_scores: dict[str, float]
    differences: dict[str, Any]
    reason: str
    suggested_action: constr(pattern="^(merge|keep_separate|needs_review)$")
