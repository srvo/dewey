from __future__ import annotations

from pydantic import BaseModel


class DataValidationConfig(BaseModel):
    """Configuration for data validation rules."""

    allowed_fields: list[str]
    pii_patterns: list[str]
    entity_mappings: dict
    min_confidence: float = 0.8


class ValidationResult(BaseModel):
    """Results of validation checks."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    pii_detected: bool
    entities_resolved: dict | None
