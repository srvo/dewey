"""Core enrichment workflow coordinating Attio and Onyx integrations."""

from datetime import datetime
from typing import Dict, List, Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from dewey.core.base_script import BaseScript
from api_clients.api_docs_manager import load_docs
from api_clients.attio_client import AttioAPIError, AttioClient
from api_clients.onyx_client import OnyxAPIError, OnyxClient
from schema import Base, OnyxEnrichment


class EnrichmentEngine(BaseScript):
    """Orchestrates the enrichment process using Attio and Onyx.

    Inherits from BaseScript for standardized configuration, logging,
    and database access.
    """

    def __init__(self) -> None:
        """Initializes the EnrichmentEngine with database and API clients."""
        super().__init__(config_section='crm', name="EnrichmentEngine")

        db_url = self.get_config_value("db_url")
        if not db_url:
            raise ValueError("Database URL not found in configuration.")

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        self.attio = AttioClient()
        self.onyx = OnyxClient()
        self.api_references = load_docs().get("links", {})

    def run(self, batch_size: int = 50) -> None:
        """Orchestrates the full enrichment workflow with error handling.

        Args:
            batch_size: The number of contacts to process in each batch.
        """
        try:
            contacts = self.attio.get_contacts(batch_size)
            self.logger.info(f"Processing {len(contacts)} contacts")

            for contact in contacts:
                self._process_contact(contact)

        except AttioAPIError as e:
            self.logger.error(f"Attio integration failed: {e}")
        except OnyxAPIError as e:
            self.logger.error(f"Onyx integration failed: {e}")

    def _process_contact(self, contact: Dict[str, Any]) -> None:
        """Handles the full lifecycle for a single contact.

        Args:
            contact: A dictionary containing the contact's information.
        """
        contact_id = contact.get("id")
        if not contact_id:
            self.logger.warning("Contact ID not found in contact data.")
            return
        try:
            self.logger.debug(f"Processing contact {contact_id}")
            enriched_data = self.onyx.universal_search(contact)
            self._store_enrichment(contact_id, contact, enriched_data)

        except Exception as e:
            self.logger.exception(f"Failed to process {contact_id}: {e}")

    def _store_enrichment(
        self, contact_id: str, raw: Dict[str, Any], enriched: Dict[str, Any]
    ) -> None:
        """Stores the enrichment results with API reference metadata.

        Args:
            contact_id: The ID of the contact.
            raw: The raw contact data.
            enriched: The enriched data.
        """
        record = {
            "schema_version": "1.0",
            "attio_reference": self.api_references.get("Attio API"),
            "onyx_reference": self.api_references.get("Onyx_ingestion"),
            "timestamp": datetime.utcnow().isoformat(),
            "contact_id": contact_id,
            "raw_contact": raw,
            "enrichment": enriched,
            "system_metadata": {
                "attio_schema_version": self.attio.schema_version,
                "onyx_request_id": enriched.get("metadata", {}).get("request_id"),
            },
        }
        self._save_to_postgres(record)

    def _save_to_postgres(self, record: Dict[str, Any]) -> None:
        """Stores a record in the PostgreSQL database with improved error handling.

        Args:
            record: A dictionary containing the record to store.
        """
        inspector = inspect(self.engine)

        if not inspector.has_table("attio_contacts") or not inspector.has_table(
            "onyx_enrichments"
        ):
            Base.metadata.create_all(self.engine)

        session = self.Session()
        try:
            self.logger.debug(
                f"Attempting to save enrichment for contact {record['contact_id']}"
            )

            enrichment = OnyxEnrichment(
                contact_id=record["contact_id"],
                search_results=record,
                timestamp=datetime.fromisoformat(record["timestamp"]),
            )

            session.add(enrichment)

            self.logger.debug(
                f"Committing enrichment for contact {record['contact_id']}"
            )
            session.commit()

            self.logger.info(
                f"Successfully saved enrichment for contact {record['contact_id']}"
            )

        except IntegrityError as e:
            session.rollback()
            self.logger.error(
                f"Database integrity error for contact {record['contact_id']}: {e}"
            )
            raise

        except OperationalError as e:
            session.rollback()
            self.logger.error(f"Database operational error: {e}")
            self.logger.info("Check database connection and retry the operation")
            raise

        except Exception as e:
            session.rollback()
            self.logger.exception(f"Unexpected database error: {e}")
            self.logger.debug(f"Failed record: {record}")
            raise

        finally:
            session.close()
            self.logger.debug("Database session closed")
