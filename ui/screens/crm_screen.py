from rich.console import Console
from rich.table import Table
from typing import List
from dewey.core.crm.models import CRMContact

class CRMInterface:
    """User interface for CRM interactions"""
    
    def __init__(self):
        self.console = Console()
        
    def display_contacts(self, contacts: List[CRMContact]):
        """Display contacts in a formatted table"""
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
                contact.phone or "N/A"
            )
            
        self.console.print(table)
