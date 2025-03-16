"""Contact relationship management agent using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class ContactAgent(DeweyBaseAgent):
    """
    Agent for analyzing and deciding on contact merges.
    """

    def __init__(self):
        """Initializes the ContactAgent."""
        super().__init__(task_type="contact")
        self.add_tools([
            Tool.from_function(self.analyze_contacts, description="Analyzes two contacts and determines if they should be merged.")
        ])

    def analyze_contacts(self, contact1: Dict[str, Any], contact2: Dict[str, Any]) -> str:
        """
        Analyzes two contacts and determines if they should be merged.

        Args:
            contact1 (Dict[str, Any]): The first contact.
            contact2 (Dict[str, Any]): The second contact.

        Returns:
            str: A string indicating whether the contacts should be merged and why.
        """
        prompt = f"""
        Analyze these contacts for potential merging:
        Contact 1: {contact1}
        Contact 2: {contact2}
        """
        result = self.run(prompt)
        return result
"""Contact relationship management agent using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class ContactAgent(DeweyBaseAgent):
    """
    Agent for analyzing and deciding on contact merges.
    """

    def __init__(self):
        """Initializes the ContactAgent."""
        super().__init__(task_type="contact")
        self.add_tools([
            Tool.from_function(self.analyze_contacts, description="Analyzes two contacts and determines if they should be merged.")
        ])

    def analyze_contacts(self, contact1: Dict[str, Any], contact2: Dict[str, Any]) -> str:
        """
        Analyzes two contacts and determines if they should be merged.

        Args:
            contact1 (Dict[str, Any]): The first contact.
            contact2 (Dict[str, Any]): The second contact.

        Returns:
            str: A string indicating whether the contacts should be merged and why.
        """
        prompt = f"""
        Analyze these contacts for potential merging:
        Contact 1: {contact1}
        Contact 2: {contact2}
        """
        result = self.run(prompt)
        return result
