from pydantic import BaseModel


class CRMContact(BaseModel):
    """Represents a CRM contact record."""

    id: int | None = None
    name: str
    email: str
    phone: str | None = None
    company: str | None = None
    last_contacted: str | None = None
    notes: str | None = None
