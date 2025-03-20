from __future__ import annotations

from pydantic import BaseModel
from dewey.core.base_script import BaseScript


class CRMContact(BaseModel):
    """Represents a CRM contact record."""

    id: int | None = None
    name: str
    email: str
    phone: str | None = None
    company: str | None = None
    last_contacted: str | None = None
    notes: str | None = None


class MyScript(BaseScript):
    def __init__(self):
        super().__init__(config_section='db')

    def run(self):
        self.logger.info("Running the script...")
        # Access configuration values using self.config
        # Example: db_url = self.config.get('db_url')
        # Implement your script logic here
        self.logger.info("Script completed.")