from typing import Optional
from pydantic import BaseModel

class CRMContact(BaseModel):
    """Represents a CRM contact record"""
    id: Optional[int] = None
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    last_contacted: Optional[str] = None
    notes: Optional[str] = None
