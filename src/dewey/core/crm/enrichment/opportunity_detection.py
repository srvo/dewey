"""Script to detect business opportunities from email content.

Dependencies:
- SQLite database with processed contacts
- Regex for opportunity detection
- pandas for data manipulation
"""

import re
import sqlite3
from typing import Any, Dict

import pandas as pd

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_db_connection


class OpportunityDetector(BaseScript):
    """Detects business opportunities from email content."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the OpportunityDetector."""
        super().__init__(*args, config_section="regex_patterns", **kwargs)
        self.opportunity_patterns: dict[str, str] = self.get_config_value("opportunity")

    def extract_opportunities(self, email_text: str) -> dict[str, bool]:
        """Extracts opportunities from email text using predefined regex patterns.

        Args:
            email_text: The text content of the email.

        Returns:
            A dictionary indicating the presence of each opportunity type.

        """
        opportunities = {}
        for key, pattern_str in self.opportunity_patterns.items():
            pattern = re.compile(pattern_str, re.IGNORECASE)
            opportunities[key] = bool(pattern.search(email_text))
        return opportunities

    def update_contacts_db(
        self, opportunities_df: pd.DataFrame, conn: sqlite3.Connection
    ) -> None:
        """Updates the contacts table in the database with detected opportunities.

        Args:
            opportunities_df: DataFrame containing email and opportunity flags.
            conn: Database connection.

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
                self.logger.error(
                    f"Error updating opportunities for {row['from_email']}: {str(e)}"
                )

    def detect_opportunities(self, conn: sqlite3.Connection) -> None:
        """Detects and flags business opportunities within emails.

        Fetches emails, identifies opportunities based on regex patterns, and
        updates the contacts database.

        Args:
            conn: Database connection.

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
        for key in self.opportunity_patterns.keys():
            df[key] = df["full_message"].apply(
                lambda text: bool(self.extract_opportunities(text).get(key, False))
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
        self.update_contacts_db(opportunities, conn)

        self.logger.info("Completed opportunity detection.")

    def run(self) -> None:
        """Runs the opportunity detection process."""
        self.logger.info("Starting opportunity detection.")
        with get_db_connection() as conn:
            self.detect_opportunities(conn)
        self.logger.info("Opportunity detection completed successfully.")


if __name__ == "__main__":
    detector = OpportunityDetector()
    detector.run()
