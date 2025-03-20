from dewey.core.base_script import BaseScript

from rich.console import Console
from rich.table import Table

from dewey.core.crm.models import CRMContact

    def run(self) -> None:
        """
        Run the script.
        """
        # TODO: Implement script logic here
        raise NotImplementedError("The run method must be implemented")


class CRMInterface(BaseScript):
    """User interface for CRM interactions."""

    def __init__(self) -> None:
        self.console = Console()

    def display_contacts(self, contacts: list[CRMContact]) -> None:
        """Display contacts in a formatted table."""
        table = Table(title="CRM Contacts")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Email")
        table.add_column("Phone")

        for contact in contacts:
            table.add_row(
                str(contact.id) if contact.id else "N/A",
                contact.name,
                contact.email,
                contact.phone or "N/A",
            )

        self.console.print(table)
