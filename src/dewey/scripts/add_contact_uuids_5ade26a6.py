# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Add UUIDs to contacts table for future anonymization support.

This script adds unique identifiers (UUIDs) to all contacts in the database that don't have one.
UUIDs are essential for:
- Anonymization of contact data
- Consistent identification across systems
- Data integrity and traceability
"""

import logging
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLASession
from sqlalchemy.orm import sessionmaker

from scripts.models import Contact  # Import necessary models

# Configure logging to track the UUID addition process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="add_contact_uuids.log",
    filemode="a",
)
logger = logging.getLogger(__name__)

# Database connection setup
engine = create_engine("sqlite:///email_data.db")
Session = sessionmaker(bind=engine)
session: SQLASession = Session()


def add_contact_uuids() -> None:
    """Add UUIDs to all contacts that don't have one in the database.

    This function:
    1. Queries the database for contacts without UUIDs
    2. Generates a new UUID for each contact
    3. Updates the contact record in the database
    4. Logs each successful update

    Raises
    ------
        Exception: If any database operation fails, the transaction is rolled back
                  and the exception is re-raised after logging

    """
    try:
        # Find all contacts without UUIDs
        contacts: list[Contact] = (
            session.query(Contact).filter(Contact.id is None).all()
        )

        # Process each contact
        for contact in contacts:
            # Generate a new UUID and assign it
            contact.id = str(uuid.uuid4())

            # Commit each change individually for better traceability
            session.commit()
            logger.info(f"Added UUID for contact email: {contact.email}")

    except Exception as e:
        # Log and handle any errors that occur during the process
        logger.exception(f"Error adding UUIDs: {e!s}")
        session.rollback()
        raise
    finally:
        # Ensure the session is always closed to prevent connection leaks
        session.close()


if __name__ == "__main__":
    """
    Main execution block for the script.

    This runs the UUID addition process with proper logging of start and completion.
    """
    logger.info("Starting to add UUIDs to contacts")
    add_contact_uuids()
    logger.info("Completed adding UUIDs to contacts")
