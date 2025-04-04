"""Tests for the CRM contacts module."""

import os
import tempfile
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dewey.core.crm.contacts.contact_consolidation import ContactConsolidation
from dewey.core.crm.contacts.csv_contact_integration import CsvContactIntegration


@pytest.fixture()
def mock_csv_file() -> Generator[str, None, None]:
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
        # Create test data
        test_data = pd.DataFrame(
            {
                "email": ["test1@example.com", "test2@example.com"],
                "first_name": ["John", "Jane"],
                "last_name": ["Doe", "Smith"],
                "company": ["ACME Inc.", "Widgets Co."],
                "job_title": ["Developer", "Manager"],
                "phone": ["123-456-7890", "987-654-3210"],
            },
        )

        # Write to CSV
        test_data.to_csv(temp_file.name, index=False)

    # Return the file path
    yield temp_file.name

    # Clean up
    os.unlink(temp_file.name)


class TestContactConsolidation:
    """Test suite for ContactConsolidation class."""

    def test_initialization(self) -> None:
        """Test ContactConsolidation initialization."""
        consolidation = ContactConsolidation()
        assert consolidation is not None
        assert consolidation.config_section == "contact_consolidation"
        assert consolidation.requires_db is True

    @patch("duckdb.DuckDBPyConnection")
    def test_create_unified_contacts_table(self, mock_conn) -> None:
        """Test creating the unified_contacts table."""
        # Setup
        consolidation = ContactConsolidation()

        # Execute
        consolidation.create_unified_contacts_table(mock_conn)

        # Verify
        mock_conn.execute.assert_called_once()
        exec_args = mock_conn.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS unified_contacts" in exec_args

    @patch("duckdb.DuckDBPyConnection")
    def test_extract_contacts_from_crm(self, mock_conn) -> None:
        """Test extracting contacts from CRM tables."""
        # Setup
        consolidation = ContactConsolidation()
        mock_conn.execute.return_value.fetchall.return_value = [
            # Mock the return data structure from the SQL query
            (
                "test@example.com",
                "Test User",
                "Test",
                "User",
                None,
                None,
                None,
                None,
                "CRM",
                "example.com",
                "2023-01-01",
                "2023-01-01",
                "2023-01-01",
                None,
                "Test notes",
                None,
            ),
        ]

        # Execute
        contacts = consolidation.extract_contacts_from_crm(mock_conn)

        # Verify
        assert len(contacts) == 1
        assert contacts[0]["email"] == "test@example.com"
        assert contacts[0]["full_name"] == "Test User"
        mock_conn.execute.assert_called_once()

    @patch("duckdb.DuckDBPyConnection")
    def test_merge_contacts(self, mock_conn) -> None:
        """Test merging contacts from different sources."""
        # Setup
        consolidation = ContactConsolidation()

        contacts = [
            {
                "email": "test@example.com",
                "full_name": "Test User",
                "source": "CRM",
                "company": None,  # Add company key with None value to avoid KeyError
            },
            {"email": "test@example.com", "company": "ACME Inc.", "source": "Email"},
        ]

        # Execute
        merged = consolidation.merge_contacts(contacts)

        # Verify
        assert len(merged) == 1
        assert "test@example.com" in merged
        assert merged["test@example.com"]["full_name"] == "Test User"
        assert merged["test@example.com"]["company"] == "ACME Inc."


class TestCsvContactIntegration:
    """Test suite for CsvContactIntegration class."""

    def test_initialization(self) -> None:
        """Test CsvContactIntegration initialization."""
        integration = CsvContactIntegration()
        assert integration is not None
        assert integration.config_section == "csv_contact_integration"
        assert integration.requires_db is True

    @patch("dewey.core.db.connection.get_connection")
    def test_process_csv(self, mock_get_connection, mock_csv_file) -> None:
        """Test processing a CSV file."""
        # Setup
        integration = CsvContactIntegration()
        mock_db = MagicMock()
        mock_get_connection.return_value = mock_db
        integration.db_conn = mock_db

        # Mock the insert_contact method
        integration.insert_contact = MagicMock()

        # Execute
        integration.process_csv(mock_csv_file)

        # Verify
        assert integration.insert_contact.call_count == 2  # Two rows in test CSV

    def test_insert_contact(self) -> None:
        """Test inserting a contact into the database."""
        # Setup
        integration = CsvContactIntegration()
        integration.db_conn = MagicMock()

        contact_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "company": "ACME Inc.",
        }

        # Execute
        integration.insert_contact(contact_data)

        # Verify
        integration.db_conn.execute.assert_called_once()

    def test_insert_contact_validation_error(self) -> None:
        """Test validation error when inserting invalid contact data."""
        # Setup
        integration = CsvContactIntegration()

        # Empty data should raise ValueError
        with pytest.raises(ValueError):
            integration.insert_contact({})

        # Invalid data type should raise TypeError
        with pytest.raises(TypeError):
            integration.insert_contact({"data": object()})
