"""
Gmail ingestion module for importing emails into PostgreSQL database.
"""
import argparse
import os
import json
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import base64

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import db_manager
from dewey.core.db.models import Emails, ClientCommunicationsIndex
from dewey.core.exceptions import DatabaseConnectionError

class GmailImporter(BaseScript):
    """Gmail email importer with idempotent PostgreSQL operations."""
    
    def __init__(self):
        super().__init__(
            name="gmail_importer",
            description="Import emails from Gmail into PostgreSQL",
            config_section="crm.gmail",
            requires_db=True
        )
        self.gmail_service = None

    def setup_argparse(self) -> argparse.ArgumentParser:
        parser = super().setup_argparse()
        parser.add_argument("--max-results", type=int, default=500,
                          help="Maximum number of emails to fetch per run")
        parser.add_argument("--batch-size", type=int, default=100,
                          help="Number of emails to process per batch")
        parser.add_argument("--label", type=str, default="INBOX",
                          help="Gmail label to process")
        return parser

    def _init_gmail_client(self) -> None:
        """Initialize Gmail API client using configured credentials."""
        try:
            creds = self._get_credentials()
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            self.logger.info("Gmail API client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gmail client: {e}")
            raise

    def _get_credentials(self) -> Credentials:
        """Retrieve credentials from config/env using BaseScript facilities."""
        creds_file = self.get_config_value("credentials_file")
        if not creds_file:
            raise ValueError("Missing credentials_file in config")

        token_path = self.get_path(creds_file)

        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Credentials file not found: {token_path}")

        try:
            with open(token_path, 'r') as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data,
                                                           scopes=self.get_config_value("gmail_scopes"))
            self.logger.debug("Credentials loaded from file")
            return creds
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            raise

    def _email_exists(self, session: Session, msg_id: str) -> bool:
        """Check if email already exists in database."""
        return session.query(Emails).get(msg_id) is not None

    def _transform_email(self, message: Dict) -> Dict:
        """Transform Gmail API response to database model format."""
        try:
            msg = self.gmail_service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            headers = msg['payload']['headers']
            
            # Extract relevant headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
            from_address = next((h['value'] for h in headers if h['name'] == 'From'), None)
            to_addresses = [h['value'] for h in headers if h['name'] == 'To']
            
            # Decode the message body
            if 'parts' in msg['payload']:
                body = '\n'.join(self._decode_part(part) for part in msg['payload']['parts'])
            else:
                body = self._decode_part(msg['payload'])

            email_data = {
                'msg_id': msg['id'],
                'thread_id': msg['threadId'],
                'subject': subject,
                'from_address': from_address,
                'to_addresses': to_addresses,
                'body_text': body,
                'raw_data': msg
            }
            return email_data
        except Exception as e:
            self.logger.error(f"Failed to transform email {message['id']}: {e}")
            raise

    def _decode_part(self, part: Dict) -> str:
        """Decode a MIME part of the email."""
        if 'data' in part['body']:
            data = part['body']['data']
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif 'parts' in part:
            return '\n'.join(self._decode_part(p) for p in part['parts'])
        return ''

    def _process_batch(self, session: Session, messages: List[Dict]) -> None:
        """Process a batch of emails with idempotent inserts."""
        new_emails = 0
        skipped = 0

        for message in messages:
            msg_id = message['id']
            if self._email_exists(session, msg_id):
                skipped += 1
                continue

            try:
                email_data = self._transform_email(message)
                email = Emails(**email_data)
                session.add(email)
                new_emails += 1
                
                # Create ClientCommunicationsIndex entry
                cci = ClientCommunicationsIndex(
                    thread_id=email.thread_id,
                    client_email=email.from_address,
                    subject=email.subject,
                    client_message=email.body_text,
                    client_msg_id=email.msg_id
                )
                session.add(cci)

            except Exception as e:
                self.logger.error(f"Failed to process email {msg_id}: {e}")

        try:
            session.commit()
            self.logger.info(f"Batch processed - New: {new_emails}, Skipped: {skipped}")
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Batch commit failed: {e}")
            raise DatabaseConnectionError("Failed to commit email batch")

    def execute(self) -> None:
        """Main execution method inherited from BaseScript."""
        args = self.parse_args()
        
        try:
            self._init_gmail_client()
            messages = self._fetch_emails(args.max_results, args.label)
            
            with db_manager.get_session() as session:
                for i in range(0, len(messages), args.batch_size):
                    batch = messages[i:i+args.batch_size]
                    self._process_batch(session, batch)
                    
            self.logger.info("Email import completed successfully")

        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
        except DatabaseConnectionError as e:
            self.logger.error(f"Database error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)

    def _fetch_emails(self, max_results: int, label: str) -> List[Dict]:
        """Fetch emails from Gmail API with error handling."""
        try:
            result = self.gmail_service.users().messages().list(
                userId='me',
                labelIds=[label],
                maxResults=max_results
            ).execute()
            return result.get('messages', [])
        except HttpError as e:
            self.logger.error(f"Failed to fetch emails: {e}")
            raise

if __name__ == "__main__":
    GmailImporter().run()
# To use this script, you'll need to:
# 1.  Create a Gmail API project and download the credentials file.
# 2.  Configure the `dewey.yaml` file with the path to the credentials file and the desired Gmail API scopes.
# 3.  Run the script with the desired command-line arguments.
# Let me know if you have any other questions or requests!
