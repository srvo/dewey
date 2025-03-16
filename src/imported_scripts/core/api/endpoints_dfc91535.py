from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import Contact, Email
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.security import django_auth

if TYPE_CHECKING:
    from datetime import datetime

api = NinjaAPI(
    title="Email Processing API",
    version="1.0.0",
    description="API for email processing and management",
    auth=django_auth,
    docs_url="/docs",
    openapi_url="/openapi.json",
    urls_namespace="core-api",
)


class EmailOut(Schema):
    id: str
    subject: str
    from_email: str
    received_at: datetime
    importance_score: float
    user_interest_score: float


class ContactOut(Schema):
    id: str
    email: str
    name: str | None


@api.get("/emails", response=list[EmailOut])
def list_emails(request):
    """List all emails with pagination."""
    return Email.objects.all()[:100]


@api.get("/emails/{email_id}", response=EmailOut)
def get_email(request, email_id: str):
    """Get a specific email by ID."""
    return get_object_or_404(Email, id=email_id)


@api.get("/contacts", response=list[ContactOut])
def list_contacts(request):
    """List all contacts."""
    return Contact.objects.all()


@api.get("/contacts/{contact_id}", response=ContactOut)
def get_contact(request, contact_id: str):
    """Get a specific contact by ID."""
    return get_object_or_404(Contact, id=contact_id)
