
import json
import re
import uuid
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.enrichment.contact_enrichment import ContactEnrichment
from dewey.utils.database import fetch_one, fetch_all


@pytest.fixture
def contact_enrichment() -> ContactEnrichment:
    """Fixture to create a ContactEnrichment instance with mocked dependencies."""
    with patch("dewey.core.crm.enrichment.contact_enrichment.get_connection") as mock_get_connection:
        mock_conn = MagicMock()
        mock_get_connection.return_value.__enter__.return_value = mock_conn
        enrichment = ContactEnrichment(name="TestEnrichment", description="Test", config_section="test_config")
        enrichment.logger = MagicMock()  # Mock the logger
        return enrichment


@pytest.fixture
def mock_db_connection(contact_enrichment: ContactEnrichment) -> MagicMock:
    """Fixture to provide a mock database connection."""
    return contact_enrichment.db_conn


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture to provide a mock configuration."""
    return {
        "regex_patterns": {
            "contact_info": {
                "name": "(.*)",
                "job_title": "(.*)",
                "company": "(.*)",
                "phone": "(.*)",
                "linkedin_url": "(.*)",
            }
        },
        "settings": {"analysis_batch_size": 50},
    }


class TestContactEnrichment:
    """Unit tests for the ContactEnrichment class."""

    def test_init(self, contact_enrichment: ContactEnrichment, mock_config: Dict[str, Any]) -> None:
        """Test the __init__ method."""
        assert contact_enrichment.name == "TestEnrichment"
        assert contact_enrichment.description == "Test"
        assert contact_enrichment.config_section == "test_config"
        assert contact_enrichment.enrichment_batch_size == 50
        assert isinstance(contact_enrichment.patterns, dict)

    def test_run(self, contact_enrichment: ContactEnrichment) -> None:
        """Test the run method."""
        with patch.object(contact_enrichment, "enrich_contacts") as mock_enrich_contacts:
            contact_enrichment.run(batch_size=100)
            mock_enrich_contacts.assert_called_once_with(100)

            contact_enrichment.run()
            mock_enrich_contacts.assert_called_with(None)

    def test_create_enrichment_task(self, contact_enrichment: ContactEnrichment, mock_db_connection: MagicMock) -> None:
        """Test the create_enrichment_task method."""
        entity_type = "email"
        entity_id = "12345"
        task_type = "contact_info"
        metadata = {"source": "email_signature"}

        mock_cursor = MagicMock()
        mock_db_connection.cursor.return_value = mock_cursor

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678123456781234567812345678")):
            task_id = contact_enrichment.create_enrichment_task(
                mock_db_connection, entity_type, entity_id, task_type, metadata
            )

        assert task_id == "12345678-1234-5678-1234-567812345678"
        mock_db_connection.cursor.assert_called_once()
        contact_enrichment.logger.info.assert_called()
        contact_enrichment.logger.debug.assert_called()
        mock_cursor.execute.assert_called_once()
        mock_db_connection.commit.assert_called_once()

        # Test exception handling
        mock_cursor.execute.side_effect = Exception("Database error")
        with pytest.raises(Exception, match="Database error"):
            contact_enrichment.create_enrichment_task(
                mock_db_connection, entity_type, entity_id, task_type, metadata
            )
        contact_enrichment.logger.error.assert_called()
        mock_db_connection.rollback.assert_called_once()

    def test_update_task_status(self, contact_enrichment: ContactEnrichment, mock_db_connection: MagicMock) -> None:
        """Test the update_task_status method."""
        task_id = "12345"
        status = "completed"
        result = {"name": "John Doe", "company": "ACME Inc"}
        error = None

        mock_cursor = MagicMock()
        mock_db_connection.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1

        contact_enrichment.update_task_status(mock_db_connection, task_id, status, result, error)

        contact_enrichment.logger.info.assert_called()
        contact_enrichment.logger.debug.assert_called()
        mock_cursor.execute.assert_called_once()
        mock_db_connection.commit.assert_called_once()

        # Test task not found
        mock_cursor.rowcount = 0
        contact_enrichment.update_task_status(mock_db_connection, task_id, status, result, error)
        contact_enrichment.logger.warning.assert_called()

        # Test exception handling
        mock_cursor.execute.side_effect = Exception("Database error")
        with pytest.raises(Exception, match="Database error"):
            contact_enrichment.update_task_status(mock_db_connection, task_id, status, result, error)
        contact_enrichment.logger.error.assert_called()
        mock_db_connection.rollback.assert_called_once()

    def test_store_enrichment_source(self, contact_enrichment: ContactEnrichment, mock_db_connection: MagicMock) -> None:
        """Test the store_enrichment_source method."""
        source_type = "email_signature"
        entity_type = "contact"
        entity_id = "12345"
        data = {"name": "John Doe", "company": "ACME Inc"}
        confidence = 0.85

        mock_cursor = MagicMock()
        mock_db_connection.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678123456781234567812345678")):
            source_id = contact_enrichment.store_enrichment_source(
                mock_db_connection, source_type, entity_type, entity_id, data, confidence
            )

        assert source_id == "12345678-1234-5678-1234-567812345678"
        contact_enrichment.logger.info.assert_called()
        contact_enrichment.logger.debug.assert_called()
        assert mock_cursor.execute.call_count == 2  # Update and Insert
        mock_db_connection.commit.assert_called_once()

        # Test exception handling
        mock_cursor.execute.side_effect = Exception("Database error")
        with pytest.raises(Exception, match="Database error"):
            contact_enrichment.store_enrichment_source(
                mock_db_connection, source_type, entity_type, entity_id, data, confidence
            )
        contact_enrichment.logger.error.assert_called()
        mock_db_connection.rollback.assert_called_once()

    @pytest.mark.parametrize(
        "message_text, expected_info",
        [
            (
                "John Doe\nCEO at ACME Inc\nPhone: 555-1234",
                {
                    "name": "John Doe",
                    "job_title": "CEO",
                    "company": "ACME Inc",
                    "phone": "555-1234",
                    "linkedin_url": None,
                    "confidence": pytest.approx(0.75),
                },
            ),
            (
                "Jane Smith\nMarketing Manager\nLinkedIn: linkedin.com/in/janesmith",
                {
                    "name": "Jane Smith",
                    "job_title": "Marketing Manager",
                    "company": None,
                    "phone": None,
                    "linkedin_url": "linkedin.com/in/janesmith",
                    "confidence": pytest.approx(0.5),
                },
            ),
            ("", None),  # Empty message
            ("Only one field", None),  # Insufficient fields
        ],
    )
    def test_extract_contact_info(
        self, contact_enrichment: ContactEnrichment, message_text: str, expected_info: Optional[Dict[str, Any]]
    ) -> None:
        """Test the extract_contact_info method with various inputs."""
        # Mock the regex patterns to return simple matches for testing
        contact_enrichment.patterns = {
            "name": "(.*)",
            "job_title": "(.*)",
            "company": "(.*)",
            "phone": "(.*)",
            "linkedin_url": "(.*)",
        }

        info = contact_enrichment.extract_contact_info(message_text)

        if expected_info:
            assert info is not None
            assert info["name"] == expected_info["name"]
            assert info["job_title"] == expected_info["job_title"]
            assert info["company"] == expected_info["company"]
            assert info["phone"] == expected_info["phone"]
            assert info["linkedin_url"] == expected_info["linkedin_url"]
            assert info["confidence"] == expected_info["confidence"]
        else:
            assert info is None

        if not message_text:
            contact_enrichment.logger.warning.assert_called_with("[EXTRACT] Empty message text provided")

    def test_extract_contact_info_exception(self, contact_enrichment: ContactEnrichment) -> None:
        """Test the extract_contact_info method with an exception."""
        message_text = "John Doe\nCEO at ACME Inc\nPhone: 555-1234"
        contact_enrichment.patterns = {
            "name": "(.*)",
            "job_title": "(.*)",
            "company": "(.*)",
            "phone": "(.*)",
            "linkedin_url": "(.*)",
        }

        # Mock re.compile to raise an exception
        with patch("re.compile", side_effect=Exception("Regex error")):
            info = contact_enrichment.extract_contact_info(message_text)
            assert info is None
            contact_enrichment.logger.error.assert_called()

    def test_process_email_for_enrichment(
        self, contact_enrichment: ContactEnrichment, mock_db_connection: MagicMock
    ) -> None:
        """Test the process_email_for_enrichment method."""
        email_id = "email_12345"
        from_email = "john.doe@example.com"
        from_name = "John Doe"
        plain_body = "John Doe\nCEO at ACME Inc\nPhone: 555-1234"
        html_body = "<html><body>John Doe\nCEO at ACME Inc\nPhone: 555-1234</body></html>"

        # Mock database results
        mock_cursor = MagicMock()
        mock_db_connection.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1

        mock_fetch_one_result = (email_id, from_email, from_name, plain_body, html_body)
        fetch_one.return_value = mock_fetch_one_result

        # Mock other methods
        contact_enrichment.create_enrichment_task = MagicMock(return_value="task_123")
        contact_enrichment.extract_contact_info = MagicMock(
            return_value={
                "name": "John Doe", "job_title": "CEO", "company": "ACME Inc", "phone": "555-1234", "linkedin_url": None, "confidence": 0.75, }
        )
        contact_enrichment.store_enrichment_source = MagicMock(return_value="source_123")
        contact_enrichment.update_task_status = MagicMock()

        # Execute the method
        success = contact_enrichment.process_email_for_enrichment(mock_db_connection, email_id)

        # Assertions
        assert success is True
        fetch_one.assert_called_once()
        contact_enrichment.create_enrichment_task.assert_called_once()
        contact_enrichment.extract_contact_info.assert_called_once_with(plain_body)
        contact_enrichment.store_enrichment_source.assert_called_once()
        contact_enrichment.update_task_status.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_db_connection.commit.assert_called_once()

        # Test email not found
        fetch_one.return_value = None
        success = contact_enrichment.process_email_for_enrichment(mock_db_connection, email_id)
        assert success is False
        contact_enrichment.logger.error.assert_called()

        # Test no contact info found
        fetch_one.return_value = mock_fetch_one_result
        contact_enrichment.extract_contact_info.return_value = None
        success = contact_enrichment.process_email_for_enrichment(mock_db_connection, email_id)
        assert success is False
        contact_enrichment.update_task_status.assert_called()

        # Test exception during processing
        contact_enrichment.extract_contact_info.side_effect = Exception("Extraction error")
        success = contact_enrichment.process_email_for_enrichment(mock_db_connection, email_id)
        assert success is False
        contact_enrichment.update_task_status.assert_called()
        contact_enrichment.logger.error.assert_called()
        mock_db_connection.rollback.assert_called_once()

        # Test fatal exception
        fetch_one.side_effect = Exception("Fetch error")
        success = contact_enrichment.process_email_for_enrichment(mock_db_connection, email_id)
        assert success is False
        contact_enrichment.logger.error.assert_called()

    def test_enrich_contacts(self, contact_enrichment: ContactEnrichment, mock_db_connection: MagicMock) -> None:
        """Test the enrich_contacts method."""
        batch_size = 2
        email_ids = ["email_1", "email_2"]

        # Mock database results
        mock_cursor = MagicMock()
        mock_db_connection.cursor.return_value = mock_cursor

        fetch_all.return_value = [(email_id, ) for email_id in email_ids]

        # Mock process_email_for_enrichment
        contact_enrichment.process_email_for_enrichment=None, match="Fetch error"):
            if ) for email_id in email_ids]

        # Mock process_email_for_enrichment
        contact_enrichment.process_email_for_enrichment is None:
                ) for email_id in email_ids]

        # Mock process_email_for_enrichment
        contact_enrichment.process_email_for_enrichment = MagicMock(return_value=True)

        # Execute the method
        contact_enrichment.enrich_contacts(batch_size)

        # Assertions
        fetch_all.assert_called_once()
        assert contact_enrichment.process_email_for_enrichment.call_count == len(email_ids)
        contact_enrichment.logger.info.assert_called()
        mock_db_connection.commit.assert_called()

        # Test no new emails
        fetch_all.return_value = []
        contact_enrichment.enrich_contacts(batch_size)
        contact_enrichment.logger.info.assert_called()

        # Test exception during processing
        fetch_all.side_effect = Exception("Fetch error")
        with pytest.raises(Exception
            contact_enrichment.enrich_contacts(batch_size)
        contact_enrichment.logger.error.assert_called()
        mock_db_connection.rollback.assert_called()
