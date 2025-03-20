from typing import Optional

from pydantic import BaseModel

from dewey.core.base_script import BaseScript


class CRMContact(BaseModel):
    """Represents a CRM contact record."""

    id: Optional[int] = None
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    last_contacted: Optional[str] = None
    notes: Optional[str] = None


class MyScript(BaseScript):
    """
    A sample script demonstrating Dewey conventions.

    Inherits from BaseScript and showcases logging, configuration access,
    and the run method.
    """

    def __init__(self) -> None:
        """Initializes the MyScript class."""
        super().__init__(config_section="db")

    def run(self) -> None:
        """
        Executes the main logic of the script.

        Logs messages and accesses configuration values.
        """
        self.logger.info("Running the script...")
        # Access configuration values using self.get_config_value()
        db_url = self.get_config_value("db_url")
        self.logger.info(f"DB URL from config: {db_url}")
        # Implement your script logic here
        self.logger.info("Script completed.")
