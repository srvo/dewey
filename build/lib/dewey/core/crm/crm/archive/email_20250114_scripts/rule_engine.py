import re
from typing import Any, Dict

from db_connector import DBConnector


class RuleEngine:
    """Core rule processing engine for email automation.

    This class handles the application of user-defined rules to incoming emails.
    Rules are stored in the database and processed in priority order.

    Attributes:
    ----------
        db: Database connector instance
        rules: List of all active rules loaded from database

    """

    def __init__(self, db_path: str = "srvo.db") -> None:
        """Initialize the RuleEngine with database connection.

        Args:
        ----
            db_path: Path to SQLite database file. Defaults to "srvo.db".

        """
        self.db = DBConnector(db_path)
        self.rules = self.db.get_all_email_rules()

    def apply_rules(self, email: Dict[str, Any]) -> None:
        """Apply all rules to a given email in priority order.

        Processes rules from highest to lowest priority. Stops after first match.
        Logs rule matches to database for tracking and analytics.

        Args:
        ----
            email: Dictionary containing email data including:
                - id: Unique email identifier
                - content: Full email text content
                - other metadata fields

        """
        # Sort rules by priority (highest first)
        for rule in sorted(self.rules, key=lambda x: x["priority"], reverse=True):
            # Check if rule pattern matches email content
            if re.search(rule["pattern"], email["content"]):
                # Execute the associated action
                self.execute_action(rule["action"], email)
                # Log the rule match for analytics
                self.db.log_rule_match(email["id"], rule["id"])
                break  # Stop after first matching rule

    def execute_action(self, action: str, email: Dict[str, Any]) -> None:
        """Execute the specified action on the email.

        Args:
        ----
            action: String identifier for the action to perform
            email: Dictionary containing email data

        Note:
        ----
            Currently implements basic actions. Can be extended with additional
            email processing capabilities as needed.

        """
        if action == "mark_as_read":
            # TODO: Implement marking email as read
            # Would need integration with email provider API
            pass
        elif action == "move_to_folder":
            # TODO: Implement moving email to a specific folder
            # Would need integration with email provider API
            pass
        # Add more actions as needed
