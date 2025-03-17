"""Pydantic schemas for Syzygy app."""

from .base import BaseSchema, generate_schema, create_input_schema
from .models import (
    ContactInputSchema,
    BulkContactInput,
    BulkContactResponse,
    ContactMerge,
    EnrichmentTaskInputSchema,
    BulkTaskInput,
    BulkTaskResponse,
    BulkAction,
    TaskResponse,
)
