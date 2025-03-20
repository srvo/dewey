import logging
from typing import List, Dict, Any, Optional

from googleapiclient.errors import HttpError

from dewey.core.base_script import BaseScript

class GmailSync(BaseScript):
    """Handles synchronization of Gmail messages."""

    def __init__(self, gmail_client):
        """
        Initializes the GmailSync class with a GmailClient instance.
        """
        super().__init__(config_section='crm')
        self.gmail_client = gmail_client

    def initial_sync(self, query: str = None, max_results: int = 1000) -> List[Dict[str, Any]]:
        """
        Performs an initial synchronization of Gmail messages.

        Args:
            query: Gmail search query (e.g., "from:user@example.com").
            max_results: Maximum number of emails to return.

        Returns:
            A list of email messages.
        """
        all_messages = []
        page_token = None
        try:
            while True:
                results = self.gmail_client.fetch_emails(query=query, max_results=max_results, page_token=page_token)
                if not results or not results.get('messages'):
                    break
                all_messages.extend(results.get('messages'))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            return all_messages
        except HttpError as error:
            self.logger.error(f"An error occurred during initial sync: {error}")
            return []

    def incremental_sync(self, start_history_id: int) -> List[Dict[str, Any]]:
        """
        Performs an incremental synchronization of Gmail messages using the History API.

        Args:
            start_history_id: The ID of the history to start syncing from.

        Returns:
            A list of history records.
        """
        history = []
        page_token = None
        try:
            while True:
                results = (
                    self.gmail_client.service.users()
                    .history()
                    .list(userId="me", startHistoryId=start_history_id, pageToken=page_token)
                    .execute()
                )
                if not results or not results.get('history'):
                    break
                history.extend(results.get('history'))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            return history
        except HttpError as error:
            self.logger.error(f"An error occurred during incremental sync: {error}")
            return []

    def run(self):
        """
        Placeholder for the run method required by BaseScript.
        """
        self.logger.info("GmailSync script is running.")
        # Add your main script logic here
        pass