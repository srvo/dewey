"""Script to detect business opportunities from email content.

Dependencies:
- SQLite database with processed contacts
- Regex for opportunity detection
- pandas for data manipulation
"""

import logging
import re
from typing import Dict

import pandas as pd
import yaml

from src.dewey.utils.database import get_db_connection
from config.logging import configure_logging

# Load the configuration file
with open("config/dewey.yaml", "r") as f:
    config = yaml.safe_load(f)

# Configure logging
configure_logging(config["logging"])

# Get logger
logger = logging.getLogger(__name__)

# Load regex patterns from config
OPPORTUNITY_PATTERNS: Dict[str, str] = config["regex_patterns"]["opportunity"]


def extract_opportunities(email_text: str) -> Dict[str, bool]:
    """Extracts opportunities from email text using predefined regex patterns.

    Args:
        email_text: The text content of the email.

    Returns:
        A dictionary indicating the presence of each opportunity type.
    """
    opportunities = {}
    for key, pattern_str in OPPORTUNITY_PATTERNS.items():
        pattern = re.compile(pattern_str, re.IGNORECASE)
        opportunities[key] = bool(pattern.search(email_text))
    return opportunities


def update_contacts_db(opportunities_df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """Updates the contacts table in the database with detected opportunities.

    Args:
        opportunities_df: DataFrame containing email and opportunity flags.
    """
    for _, row in opportunities_df.iterrows():
        try:
            conn.execute(
                """
            UPDATE contacts
            SET
                demo_opportunity = ?,
                cancellation_request = ?,
                speaking_opportunity = ?,
                publicity_opportunity = ?,
                paper_submission_opportunity = ?
            WHERE email = ?
            """,
                (
                    row["demo"],
                    row["cancellation"],
                    row["speaking"],
                    row["publicity"],
                    row["submission"],
                    row["from_email"],
                ),
            )
        except Exception as e:
            logger.error(
                f"Error updating opportunities for {row['from_email']}: {str(e)}"
            )


def detect_opportunities(conn: sqlite3.Connection) -> None:
    """Detects and flags business opportunities within emails.

    Fetches emails, identifies opportunities based on regex patterns, and updates the contacts database.
    """
    query = """
    SELECT
        e.message_id,
        e.from_email,
        e.subject,
        e.full_message
    FROM raw_emails e
    JOIN processed_contacts pc ON e.message_id = pc.message_id
    """
    df = pd.read_sql_query(query, conn)

    # Initialize new columns for each opportunity type, defaulting to False
    for key in OPPORTUNITY_PATTERNS.keys():
        df[key] = df["full_message"].apply(
            lambda text: bool(extract_opportunities(text).get(key, False))
        )

    # Aggregate opportunities per contact
    opportunities = (
        df.groupby("from_email")
        .agg(
            {
                "demo": "any",
                "cancellation": "any",
                "speaking": "any",
                "publicity": "any",
                "submission": "any",
            }
        )
        .reset_index()
    )

    # Update the contacts table with detected opportunities
    update_contacts_db(opportunities, conn)

    logger.info("Completed opportunity detection.")


if __name__ == "__main__":
    logger.info("Starting opportunity detection.")
    with get_db_connection() as conn:
        detect_opportunities(conn)
    logger.info("Opportunity detection completed successfully.")
