"""Base schema generation utilities for Django models."""

from typing import Type, Dict, Any, Optional, List, Union
from datetime import datetime
from django.db import models
from pydantic import BaseModel, Field, create_model, ConfigDict
from django.core.exceptions import FieldDoesNotExist
import uuid


class BaseSchema(BaseModel):
    """Base schema with common configurations."""

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={datetime: lambda v: v.isoformat(), uuid.UUID: lambda v: str(v)},
    )


def get_field_type(field: models.Field) -> tuple:
    """Get the appropriate Pydantic field type for a Django model field."""
    type_mapping = {
        models.CharField: (str, ...),
        models.TextField: (str, ...),
        models.IntegerField: (int, ...),
        models.FloatField: (float, ...),
        models.DecimalField: (float, ...),
        models.BooleanField: (bool, ...),
        models.DateTimeField: (datetime, ...),
        models.DateField: (datetime, ...),
        models.EmailField: (str, ...),
        models.URLField: (str, ...),
        models.UUIDField: (uuid.UUID, ...),
        models.JSONField: (Dict[str, Any], ...),
        models.ForeignKey: (int, ...),  # We'll store the ID for foreign keys
        models.ManyToManyField: (List[int], ...),  # List of IDs for M2M
    }

    # Handle nullable fields
    if field.null:
        base_type = type_mapping.get(field.__class__, (Any, ...))[0]
        return (Optional[base_type], None)

    return type_mapping.get(field.__class__, (Any, ...))


def generate_schema(
    model: Type[models.Model],
    name: str = None,
    exclude: List[str] = None,
    include: List[str] = None,
    base_schema: Type[BaseModel] = BaseSchema,
) -> Type[BaseModel]:
    """Generate a Pydantic schema from a Django model.

    Args:
        model: Django model class
        name: Name for the generated schema (defaults to ModelNameSchema)
        exclude: List of field names to exclude
        include: List of field names to include (if None, includes all)
        base_schema: Base schema class to inherit from

    Returns:
        A Pydantic model class for the Django model
    """
    exclude = exclude or []
    schema_name = name or f"{model.__name__}Schema"
    fields: Dict[str, Any] = {}

    for field in model._meta.get_fields():
        # Skip if field should be excluded
        if field.name in exclude:
            continue

        # Skip if we have an include list and field is not in it
        if include and field.name not in include:
            continue

        # Handle special fields
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            # For foreign keys, we'll include both ID and a nested representation
            fields[field.name + "_id"] = get_field_type(field)
            # We'll handle the nested schema later with a lazy reference
            continue

        elif isinstance(field, models.ManyToManyField):
            # For M2M, we'll include list of IDs and handle nested schema later
            fields[field.name + "_ids"] = (List[int], [])
            continue

        # Get the field type
        field_type = get_field_type(field)
        fields[field.name] = field_type

        # Add description if available
        if field.help_text:
            fields[field.name] = (
                field_type[0],
                Field(..., description=field.help_text),
            )

    # Create the schema class
    schema = create_model(schema_name, __base__=base_schema, **fields)

    return schema


def create_input_schema(
    model: Type[models.Model],
    name: str = None,
    exclude: List[str] = None,
    include: List[str] = None,
) -> Type[BaseModel]:
    """Create an input schema for creating/updating a model.

    This differs from the regular schema in that it:
    - Makes all fields optional (for partial updates)
    - Excludes auto-generated fields
    - Simplifies relationships to IDs
    """
    exclude = exclude or []
    exclude.extend(
        [
            "id",
            "created_at",
            "updated_at",  # Common auto fields
            "created_by",
            "updated_by",  # Common user tracking fields
        ]
    )

    schema = generate_schema(
        model,
        name=name or f"{model.__name__}InputSchema",
        exclude=exclude,
        include=include,
    )

    # Make all fields optional for partial updates
    new_fields = {
        name: (Optional[field.annotation], None)
        for name, field in schema.model_fields.items()
    }

    return create_model(schema.__name__, __base__=BaseSchema, **new_fields)
