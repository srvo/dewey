"""Script to detect business opportunities from email content.
Dependencies:
- SQLite database with processed contacts
- Regex for opportunity detection
- pandas for data manipulation
"""

import logging
import re

import pandas as pd

from scripts.db_connector import get_db

# Initialize logging to capture INFO and ERROR level logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)

# Define regex patterns to identify various business opportunities within email content
OPPORTUNITY_PATTERNS = {
    "demo": re.compile(r"\bdemo\b|\bschedule a demo\b", re.IGNORECASE),
    "cancellation": re.compile(r"\bcancel\b|\bneed to cancel\b", re.IGNORECASE),
    "speaking": re.compile(r"\bspeaking opportunity\b|\bpresentation\b", re.IGNORECASE),
    "publicity": re.compile(r"\bpublicity opportunity\b|\bmedia\b", re.IGNORECASE),
    "submission": re.compile(r"\bpaper submission\b|\bsubmit a paper\b", re.IGNORECASE),
}


def detect_opportunities():
    """Detects and flags business opportunities within emails based on predefined regex patterns.
    Updates the contacts database with identified opportunities.
    """
    db = get_db()
    with db.get_connection() as conn:
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
            lambda text: bool(OPPORTUNITY_PATTERNS[key].search(text))
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
    with db.get_connection() as conn:
        for _, row in opportunities.iterrows():
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

    logger.info("Completed opportunity detection.")


if __name__ == "__main__":
    logger.info("Starting opportunity detection.")
    detect_opportunities()
    logger.info("Opportunity detection completed successfully.")
