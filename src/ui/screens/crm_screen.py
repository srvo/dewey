from dewey.core.base_script import BaseScript
from dewey.core.crm.models import CRMContact
from rich.console import Console
from rich.table import Table


class CRMInterface(BaseScript):
    """User interface for CRM interactions."""

    def __init__(self) -> None:
        super().__init__(requires_db=True)
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

    def execute(self) -> None:
        """Fetch and display CRM contacts."""
        try:
            with self.db_session_scope() as session:
                contacts = session.query(CRMContact).all()
            self.display_contacts(contacts)
        except Exception as e:
            self.logger.error(f"Error fetching CRM contacts: {e}")
            self.console.print(f"Error: {e}", style="red")
