#!/usr/bin/env python3
"""
Example of the event-driven architecture in Dewey.

This example shows how to use the event bus for cross-module communication,
demonstrating the decoupled module interaction pattern.
"""

import logging
from typing import Any, Dict

from dewey.core.base_script import BaseScript
from dewey.core.events import event_bus


class ContactPublisher(BaseScript):
    """Publishes contact-related events."""
    
    def __init__(self):
        """Initialize the contact publisher."""
        super().__init__(
            name="ContactPublisher",
            description="Publishes contact-related events",
            config_section="examples",
        )
    
    def execute(self) -> None:
        """Execute the contact publisher logic."""
        self.logger.info("Contact publisher started")
        
        # Create and publish a contact event
        contact_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "company": "Acme Corp",
            "source": "website",
        }
        
        # Publish the event
        handlers_called = event_bus.publish("contact_discovered", contact_data)
        self.logger.info(f"Published contact_discovered event, {handlers_called} handlers called")
        
        # Publish another event
        company_data = {
            "name": "Acme Corp",
            "industry": "Technology",
            "size": "Medium",
        }
        handlers_called = event_bus.publish("company_info_updated", company_data)
        self.logger.info(f"Published company_info_updated event, {handlers_called} handlers called")


class ResearchSubscriber(BaseScript):
    """Subscribes to contact and company events for research purposes."""
    
    def __init__(self):
        """Initialize the research subscriber."""
        super().__init__(
            name="ResearchSubscriber",
            description="Processes contacts for research",
            config_section="examples",
        )
        
        # Subscribe to events
        event_bus.subscribe("contact_discovered", self._handle_contact)
        event_bus.subscribe("company_info_updated", self._handle_company)
    
    def _handle_contact(self, contact_data: Dict[str, Any]) -> None:
        """
        Handle a contact event.
        
        Args:
            contact_data: The contact data from the event
        """
        self.logger.info(f"Research module received contact: {contact_data['name']}")
        self.logger.info(f"Will research company: {contact_data.get('company', 'Unknown')}")
    
    def _handle_company(self, company_data: Dict[str, Any]) -> None:
        """
        Handle a company event.
        
        Args:
            company_data: The company data from the event
        """
        self.logger.info(f"Research module received company info: {company_data['name']}")
        self.logger.info(f"Industry: {company_data.get('industry', 'Unknown')}")
    
    def execute(self) -> None:
        """Execute the research subscriber logic."""
        self.logger.info("Research subscriber started and listening for events")
        # In a real app, this might start a service that listens continuously
        # For this example, we just wait for events in main()


class BookkeepingSubscriber(BaseScript):
    """Subscribes to contact events for bookkeeping purposes."""
    
    def __init__(self):
        """Initialize the bookkeeping subscriber."""
        super().__init__(
            name="BookkeepingSubscriber",
            description="Processes contacts for bookkeeping",
            config_section="examples",
        )
        
        # Subscribe to events
        event_bus.subscribe("contact_discovered", self._handle_contact)
    
    def _handle_contact(self, contact_data: Dict[str, Any]) -> None:
        """
        Handle a contact event.
        
        Args:
            contact_data: The contact data from the event
        """
        self.logger.info(f"Bookkeeping module received contact: {contact_data['name']}")
        self.logger.info("Adding to potential clients list")
    
    def execute(self) -> None:
        """Execute the bookkeeping subscriber logic."""
        self.logger.info("Bookkeeping subscriber started and listening for events")
        # In a real app, this might start a service that listens continuously


def main() -> None:
    """Execute the example."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Create subscribers first (they need to be listening before events are published)
    research = ResearchSubscriber()
    bookkeeping = BookkeepingSubscriber()
    
    # Execute the subscribers (in a real app, this might start background tasks)
    research.execute()
    bookkeeping.execute()
    
    # Create and execute the publisher
    publisher = ContactPublisher()
    publisher.execute()
    
    print("\nExample complete! The event system allowed:")
    print("1. ContactPublisher to publish events without knowing who would receive them")
    print("2. ResearchSubscriber and BookkeepingSubscriber to process events independently")
    print("3. Complete decoupling between modules\n")


if __name__ == "__main__":
    main() 