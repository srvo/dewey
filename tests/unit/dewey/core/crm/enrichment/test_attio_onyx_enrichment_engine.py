tests / unit / dewey / core / crm / enrichment / test_attio_onyx_enrichment_engine.py
"""Unit tests for the attio_onyx_enrichment_engine module."""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.enrichment.attio_onyx_enrichment_engine import EnrichmentEngine
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient
from api_clients.attio_client import AttioAPIError, AttioClient
from api_clients.onyx_client import OnyxAPIError, OnyxClient


@pytest.fixture
def enrichment_engine() -> EnrichmentEngine:
    """Fixture for creating an EnrichmentEngine instance with mocked dependencies."""
    engine = EnrichmentEngine()
    engine.attio = MagicMock(spec=AttioClient)
    engine.onyx = MagicMock(spec=OnyxClient)
    engine.db_conn = MagicMock(spec=DatabaseConnection)
    engine.llm_client = MagicMock(spec=LLMClient)
    engine.logger = MagicMock(spec=logging.Logger)
    engine.api_references = {
        "Attio API": "attio_api_url",
        "Onyx_ingestion": "onyx_api_url",
    }
    return engine


def test_enrichment_engine_initialization(enrichment_engine: EnrichmentEngine) -> None:
    """Test that the EnrichmentEngine initializes correctly."""
    assert enrichment_engine.name == "EnrichmentEngine"
    assert enrichment_engine.config_section == "crm"
    assert enrichment_engine.requires_db is True
    assert isinstance(enrichment_engine.attio, MagicMock)
    assert isinstance(enrichment_engine.onyx, MagicMock)
    assert isinstance(enrichment_engine.db_conn, MagicMock)
    assert isinstance(enrichment_engine.logger, MagicMock)
    assert enrichment_engine.api_references == {
        "Attio API": "attio_api_url",
        "Onyx_ingestion": "onyx_api_url",
    }


def test_run_success(enrichment_engine: EnrichmentEngine) -> None:
    """Test the run method with successful Attio and Onyx API calls."""
    mock_contacts = [{"id": "123"}, {"id": "456"}]
    enrichment_engine.attio.get_contacts.return_value = mock_contacts
    enrichment_engine._process_contact = MagicMock()

    enrichment_engine.run(batch_size=2)

    enrichment_engine.attio.get_contacts.assert_called_once_with(2)
    assert enrichment_engine._process_contact.call_count == len(mock_contacts)
    enrichment_engine._process_contact.assert_called_with(mock_contacts[-1])
    enrichment_engine.logger.info.assert_called_with("Processing 2 contacts")


def test_run_attio_api_error(enrichment_engine: EnrichmentEngine) -> None:
    """Test the run method when the Attio API raises an error."""
    enrichment_engine.attio.get_contacts.side_effect = AttioAPIError("Attio failed")

    with pytest.raises(AttioAPIError):
        enrichment_engine.run(batch_size=50)

    enrichment_engine.logger.error.assert_called_once_with(
        "Attio integration failed: Attio failed"
    )


def test_run_onyx_api_error(enrichment_engine: EnrichmentEngine) -> None:
    """Test the run method when the Onyx API raises an error."""
    enrichment_engine.attio.get_contacts.return_value = [{"id": "123"}]
    enrichment_engine._process_contact.side_effect = OnyxAPIError("Onyx failed")

    with pytest.raises(OnyxAPIError):
        enrichment_engine.run(batch_size=50)

    enrichment_engine.logger.error.assert_called_once_with(
        "Onyx integration failed: Onyx failed"
    )


def test_process_contact_success(enrichment_engine: EnrichmentEngine) -> None:
    """Test the _process_contact method with successful Onyx API call and data storage."""
    contact = {"id": "123", "name": "John Doe"}
    enriched_data = {"company": "Example Corp"}
    enrichment_engine.onyx.universal_search.return_value = enriched_data
    enrichment_engine._store_enrichment = MagicMock()

    enrichment_engine._process_contact(contact)

    enrichment_engine.onyx.universal_search.assert_called_once_with(contact)
    enrichment_engine._store_enrichment.assert_called_once_with(
        "123", contact, enriched_data
    )
    enrichment_engine.logger.debug.assert_called_with("Processing contact 123")


def test_process_contact_missing_id(enrichment_engine: EnrichmentEngine) -> None:
    """Test the _process_contact method when the contact data is missing an ID."""
    contact = {"name": "John Doe"}

    enrichment_engine._process_contact(contact)

    enrichment_engine.onyx.universal_search.assert_not_called()
    enrichment_engine._store_enrichment.assert_not_called()
    enrichment_engine.logger.warning.assert_called_with(
        "Contact ID not found in contact data."
    )


def test_process_contact_exception(enrichment_engine: EnrichmentEngine) -> None:
    """Test the _process_contact method when an exception occurs during processing."""
    contact = {"id": "123", "name": "John Doe"}
    enrichment_engine.onyx.universal_search.side_effect = ValueError("Search failed")

    enrichment_engine._process_contact(contact)

    enrichment_engine.logger.exception.assert_called_with(
        "Failed to process 123: Search failed"
    )


def test_store_enrichment_success(enrichment_engine: EnrichmentEngine) -> None:
    """Test the _store_enrichment method with successful data storage."""
    contact_id = "123"
    raw_data = {"name": "John Doe"}
    enriched_data = {"company": "Example Corp", "metadata": {"request_id": "req123"}}
    enrichment_engine._save_to_postgres = MagicMock()

    enrichment_engine._store_enrichment(contact_id, raw_data, enriched_data)

    enrichment_engine._save_to_postgres.assert_called_once()
    args, _ = enrichment_engine._save_to_postgres.call_args
    record = args[0]
    assert record["contact_id"] == contact_id
    assert record["raw_contact"] == raw_data
    assert record["enrichment"] == enriched_data
    assert (
        record["system_metadata"]["attio_schema_version"]
        == enrichment_engine.attio.schema_version
    )
    assert record["system_metadata"]["onyx_request_id"] == "req123"
    assert record["attio_reference"] == "attio_api_url"
    assert record["onyx_reference"] == "onyx_api_url"
    datetime.fromisoformat(
        record["timestamp"]
    )  # asserts that timestamp is a valid isoformat


def test_save_to_postgres_success(enrichment_engine: EnrichmentEngine) -> None:
    """Test the _save_to_postgres method with successful database interaction."""
    record = {
        "contact_id": "123",
        "search_results": {"company": "Example Corp"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    enrichment_engine.db_conn.add = MagicMock()
    enrichment_engine.db_conn.commit = MagicMock()
    enrichment_engine.db_conn.close = MagicMock()

    enrichment_engine._save_to_postgres(record)

    enrichment_engine.db_conn.add.assert_called_once()
    enrichment_engine.db_conn.commit.assert_called_once()
    enrichment_engine.db_conn.close.assert_called_once()
    enrichment_engine.logger.info.assert_called_with(
        "Successfully saved enrichment for contact 123"
    )


def test_save_to_postgres_failure(enrichment_engine: EnrichmentEngine) -> None:
    """Test the _save_to_postgres method when a database error occurs."""
    record = {
        "contact_id": "123",
        "search_results": {"company": "Example Corp"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    enrichment_engine.db_conn.add.side_effect = ValueError("Database error")
    enrichment_engine.db_conn.rollback = MagicMock()
    enrichment_engine.db_conn.close = MagicMock()

    with pytest.raises(ValueError):
        enrichment_engine._save_to_postgres(record)

    enrichment_engine.db_conn.rollback.assert_called_once()
    enrichment_engine.db_conn.close.assert_called_once()
    enrichment_engine.logger.exception.assert_called_with(
        "Failed to save enrichment for contact 123: Database error"
    )


@patch("dewey.core.crm.enrichment.attio_onyx_enrichment_engine.datetime")
def test_store_enrichment_timestamp(
    mock_datetime, enrichment_engine: EnrichmentEngine
) -> None:
    """Test that _store_enrichment uses the current UTC timestamp."""
    mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 0, 0, 0)
    contact_id = "123"
    raw_data = {"name": "John Doe"}
    enriched_data = {"company": "Example Corp", "metadata": {"request_id": "req123"}}
    enrichment_engine._save_to_postgres = MagicMock()

    enrichment_engine._store_enrichment(contact_id, raw_data, enriched_data)

    enrichment_engine._save_to_postgres.assert_called_once()
    args, _ = enrichment_engine._save_to_postgres.call_args
    record = args[0]
    assert record["timestamp"] == "2024-01-01T00:00:00"
