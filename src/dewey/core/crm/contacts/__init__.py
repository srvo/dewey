"""
Contact Management Module for CRM

This module contains classes and utilities for managing contacts in the CRM system,
including contact consolidation and CSV import functionality.
"""

from dewey.core.crm.contacts.contact_consolidation import ContactConsolidation
from dewey.core.crm.contacts.csv_contact_integration import CsvContactIntegration

__all__ = ["ContactConsolidation", "CsvContactIntegration"]
