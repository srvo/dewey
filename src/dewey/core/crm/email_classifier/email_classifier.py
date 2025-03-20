#!/usr/bin/env python3
"""Email classifier for Gmail using Deepinfra API for prioritization."""
import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List

import duckdb
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow  # pylint: disable=unused-import
from openai import OpenAI
import google.auth.exceptions
import google.auth.transport.requests
import requests

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.llm.llm_utils import call_llm

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.expanduser("~"), "crm", ".env"))


class EmailClassifier(BaseScript):
    """Email classifier for Gmail using Deepinfra API for prioritization."""

    def __init__(self):
        """Initializes the EmailClassifier."""
        super().__init__(
            name="EmailClassifier",
            description="Classifies emails using Deepinfra API for prioritization.",
            config_section="email_classifier",
            requires_db=True,
            enable_llm=True,
        )
        self.output_dir = "/Users/srvo/input_data/ActiveData"  # TODO: Move to config
        os.makedirs(self.output_dir, exist_ok=True)  # Ensure directory exists
        self.SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
        self.CREDENTIALS_FILE = "credentials.json"
        self.TOKEN_FILE = "token.json"
        self.PREFERENCES_FILE = "email_preferences.json"
        self.EMAIL_ANALYSIS_PROMPT_FILE = "email_analysis.txt"
        self.FEEDBACK_FILE = "/Users/srvo/lake/read/feedback.json"
        self.PRIORITY_LABELS = {
            4: "Priority/Critical",
            3: "Priority/High",
            2: "Priority/Medium",
            1: "Priority/Low",
            0: "Priority/Very Low",
        }
        self.REVIEW_LABEL = "1_For_Review"

    def get_gmail_service(self):
        """Authenticates with the Gmail API and returns the service object.

        Returns:
            The Gmail service object.

        Raises:
            google.auth.exceptions.RefreshError: If the token refresh fails.
        """
        creds = None
        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(google.auth.transport.requests.Request())
                except google.auth.exceptions.RefreshError as e:
                    self.logger.error(f"Error refreshing token: {e}")
                    self.logger.info("Deleting token file and re-authenticating...")
                    os.remove(self.TOKEN_FILE)
                    return self.get_gmail_service()
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_FILE, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        service = build("gmail", "v1", credentials=creds)
        return service

    def get_message_body(self, service, user_id, msg_id):
        """Retrieves the full message body.

        Args:
            service: The Gmail service object.
            user_id: The user ID.
            msg_id: The message ID.

        Returns:
            The message body as a string.

        Raises:
            HttpError: If an error occurs while retrieving the message.
        """
        try:
            message = (
                service.users()
                .messages()
                .get(userId=user_id, id=msg_id, format="full")
                .execute()
            )
            payload = message["payload"]

            if "parts" in payload:
                parts = payload["parts"]
                body = ""
                for part in parts:
                    if "data" in part["body"]:
                        if part["mimeType"] == "text/html":
                            body = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8", "ignore")
                            break
                        elif part["mimeType"] == "text/plain" and not body:
                            body = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8", "ignore")
                return body
            elif "body" in payload and "data" in payload["body"]:
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                    "utf-8", "ignore"
                )

            return ""

        except HttpError as error:
            self.logger.error(f"An error occurred: {error}")
            return ""

    def analyze_email_with_deepinfra(
        self, message_body: str, subject: str, from_header: str, prompt: str
    ) -> dict:
        """Analyzes email content using the DeepInfra API.

        Args:
            message_body: The email message body.
            subject: The email subject.
            from_header: The email from header.
            prompt: The prompt for the LLM.

        Returns:
            A dictionary containing the analysis results.
        """
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that responds with valid JSON"},
                {
                    "role": "user",
                    "content": f"{prompt}\n\nEmail Content:\nSubject: {subject}\nFrom: {from_header}\nBody: {message_body}"
                }
            ]
            result = call_llm(self.llm_client, messages, response_format={"type": "json_object"})

            # Validate required structure
            if not all(key in result for key in ('scores', 'metadata')):
                raise ValueError("Missing required 'scores' or 'metadata' fields")

            # Validate and normalize scoring values
            for category in ['scores', 'metadata']:
                if category not in result:
                    self.logger.warning(f"Validation error: Missing {category} section")
                    return {}

            # Add debug logging of valid result
            self.logger.debug(f"🔍 Analysis results for message:")
            self.logger.debug(f"   Priority: {result.get('priority', 'N/A')}")
            self.logger.debug(f"   Scores: { {k: v['score'] for k, v in result['scores'].items()} }")
            self.logger.debug(f"   Source: {result['metadata'].get('source', 'Unknown')}")

            return result

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API Request Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"HTTP Status: {e.response.status_code}")
                self.logger.error(f"Response Body: {e.response.text[:200]}...")  # Show first 200 chars
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected Error: {str(e)}")
            return {}

    def extract_message_parts(self, payload: Dict) -> List[Dict]:
        """Recursively extract message parts from payload.

        Args:
            payload: The message payload.

        Returns:
            A list of message parts.
        """
        parts = []

        def _extract_part(part):
            part_info = {
                'partId': part.get('partId'),
                'mimeType': part.get('mimeType'),
                'filename': part.get('filename'),
                'headers': {h['name']: h['value'] for h in part.get('headers', [])},
                'bodySize': part.get('body', {}).get('size', 0)
            }
            if 'parts' in part:
                part_info['parts'] = [_extract_part(p) for p in part['parts']]
            return part_info

        return _extract_part(payload)

    def extract_attachments(self, payload: Dict) -> List[Dict]:
        """Extract attachment information from message parts.

        Args:
            payload: The message payload.

        Returns:
            A list of attachment information.
        """
        attachments = []

        def _scan_parts(part):
            if part.get('body', {}).get('attachmentId'):
                attachments.append({
                    'attachmentId': part['body']['attachmentId'],
                    'filename': part.get('filename'),
                    'mimeType': part.get('mimeType'),
                    'size': part['body'].get('size')
                })
            if 'parts' in part:
                for p in part['parts']:
                    _scan_parts(p)

        _scan_parts(payload)
        return attachments

    def _calculate_uncertainty(self, scores: Dict) -> float:
        """Calculate uncertainty as coefficient of variation of scores.

        Args:
            scores: A dictionary of scores.

        Returns:
            The uncertainty score.
        """
        score_values = []
        for key in ['automation_score', 'content_value', 'human_interaction', 'time_value', 'business_impact']:
            score = scores.get(key, {}).get('score', 0.0)
            # Handle case where score comes in as direct float
            if isinstance(score, (int, float)):
                score_values.append(float(score))
            else:
                score_values.append(0.0)

        if not score_values:
            return 1.0  # Max uncertainty if no scores

        mean = sum(score_values) / len(score_values)
        variance = sum((x - mean) ** 2 for x in score_values) / len(score_values)
        return round(variance, 4)

    def calculate_priority(self, analysis_result: Dict, preferences: Dict) -> int:
        """Calculates email priority.

        Args:
            analysis_result: The analysis result dictionary.
            preferences: The email preferences dictionary.

        Returns:
            The calculated priority.
        """
        if not analysis_result or not analysis_result.get("scores"):
            return 2

        scores = analysis_result["scores"]
        metadata = analysis_result["metadata"]

        for rule in preferences.get("override_rules", []):
            for keyword in rule["keywords"]:
                if (
                    keyword.lower() in metadata.get("topics", [])
                    or keyword.lower() in metadata.get("source", "").lower()
                ):
                    return rule["min_priority"]

        for source in preferences.get("high_priority_sources", []):
            for keyword in source["keywords"]:
                if (
                    keyword.lower() in metadata.get("topics", [])
                    or keyword.lower() in metadata.get("source", "").lower()
                ):
                    return source["min_priority"]

        for source in preferences.get("low_priority_sources", []):
            for keyword in source["keywords"]:
                if (keyword.lower() in metadata.get("topics", [])) or (
                    keyword.lower() in metadata.get("source", "").lower()
                ):
                    return source["max_priority"]

        for newsletter_name, newsletter_details in preferences.get(
            "newsletter_defaults", {}
        ).items():
            for keyword in newsletter_details["keywords"]:
                if (
                    keyword.lower() in metadata.get("topics", [])
                    or keyword.lower() in metadata.get("source", "").lower()
                ):
                    return newsletter_details["default_priority"]

        weighted_average = (
            (1 - scores["automation_score"]["score"]) * 0.1
            + scores["content_value"]["score"] * 0.4
            + scores["human_interaction"]["score"] * 0.2
            + scores["time_value"]["score"] * 0.1
            + scores["business_impact"]["score"] * 0.2
        )
        priority = 4 - round(weighted_average * 4)
        priority = max(0, min(priority, 4))
        return priority

    def create_or_get_label_id(self, service, label_name: str) -> str:
        """Creates/gets a label ID.

        Args:
            service: The Gmail service object.
            label_name: The name of the label.

        Returns:
            The label ID.
        """
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        for label in labels:
            if label["name"] == label_name:
                return label["id"]

        label = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created_label = service.users().labels().create(userId="me", body=label).execute()
        return created_label["id"]

    def store_analysis_result(self, msg_id: str, subject: str, from_address: str, analysis_result: dict, priority: int, message_full: dict):
        """Stores analysis results in DuckDB using batch insertion.

        Args:
            msg_id: The message ID.
            subject: The email subject.
            from_address: The email from address.
            analysis_result: The analysis result dictionary.
            priority: The email priority.
            message_full: The full message dictionary.
        """
        try:
            # Get fresh connection from pool
            with get_connection().cursor() as cursor:  # Use context manager
                # Convert all values to database types explicitly
                params = (
                    msg_id,
                    message_full.get('threadId'),
                    subject,
                    from_address,
                    datetime.now(timezone.utc).isoformat(),  # ISO format for timestamp
                    json.dumps(analysis_result),
                    float(analysis_result.get('scores', {}).get('automation_score', {}).get('score', 0.0)),
                    float(analysis_result.get('scores', {}).get('content_value', {}).get('score', 0.0)),
                    float(analysis_result.get('scores', {}).get('human_interaction', {}).get('score', 0.0)),
                    float(analysis_result.get('scores', {}).get('time_value', {}).get('score', 0.0)),
                    float(analysis_result.get('scores', {}).get('business_impact', {}).get('score', 0.0)),
                    float(self._calculate_uncertainty(analysis_result.get('scores', {}))),
                    json.dumps(analysis_result.get('metadata', {})),
                    int(priority),
                    json.dumps(message_full.get('labelIds', [])),
                    message_full.get('snippet', ''),
                    int(message_full.get('internalDate', 0)),
                    int(message_full.get('sizeEstimate', 0)),
                    json.dumps(self.extract_message_parts(message_full.get('payload', {}))),
                    message_full.get('draftId'),  # NULL as None is handled automatically
                    json.dumps(message_full.get('draftMessage')) if message_full.get('draftMessage') else None,
                    json.dumps(self.extract_attachments(message_full.get('payload', {})))
                )

                # Use proper parameter binding (21 parameters now)
                cursor.execute("""
                    INSERT INTO email_analyses
                    (msg_id, thread_id, subject, from_address, analysis_date, raw_analysis,
                     automation_score, content_value, human_interaction, time_value, business_impact,
                     uncertainty_score, metadata, priority, label_ids, snippet, internal_date,
                     size_estimate, message_parts, draft_id, draft_message, attachments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (msg_id) DO UPDATE SET
                        subject = EXCLUDED.subject,
                        from_address = EXCLUDED.from_address,
                        analysis_date = EXCLUDED.analysis_date,
                        raw_analysis = EXCLUDED.raw_analysis,
                        automation_score = EXCLUDED.automation_score,
                        content_value = EXCLUDED.content_value,
                        human_interaction = EXCLUDED.human_interaction,
                        time_value = EXCLUDED.time_value,
                        business_impact = EXCLUDED.business_impact,
                        uncertainty_score = EXCLUDED.uncertainty_score,
                        metadata = EXCLUDED.metadata,
                        priority = EXCLUDED.priority
                """, params)

            self.logger.info(f"Successfully stored analysis for {msg_id} in DuckDB")
        except duckdb.Error as e:
            self.logger.error(f"Database error storing analysis: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error storing analysis: {str(e)}")
            raise

    def get_critical_emails(self, conn, limit: int = 10) -> List[Dict]:
        """Retrieve critical priority emails from database

        Args:
            conn: DuckDB connection object
            limit: Max number of emails to retrieve

        Returns:
            List of dictionaries containing email info
        """
        result = conn.execute("""
            SELECT msg_id, subject, snippet, from_address 
            FROM email_analyses 
            WHERE priority = 4 
            ORDER BY analysis_date DESC 
            LIMIT ?
        """, [limit]).fetchall()

        columns = [col[0] for col in conn.description]
        return [dict(zip(columns, row)) for row in result]

    def generate_draft_response(self, service, email: Dict) -> str:
        """Generate draft response using Hermes-3-Llama-3.1-405B model

        Args:
            service: Gmail service object
            email: Dictionary containing email info

        Returns:
            Draft response string
        """
        client = OpenAI(
            base_url="https://api.deepinfra.com/v1/openai",
            api_key=self.get_config_value("settings.deepinfra_api_key")
        )

        prompt = f"""
You are an executive assistant drafting responses to high-priority emails. Create a professional, concise response based on this email:

From: {email['from_address']}
Subject: {email['subject']}
Content: {email['snippet']}

Guidelines:
- Acknowledge receipt immediately
- Outline next steps clearly
- Maintain professional tone
- Keep under 3 paragraphs
- Include placeholder brackets for details [like this]
"""

        response = client.chat.completions.create(
            model="NousResearch/Hermes-3-Llama-3.1-405B",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content

    def create_draft(self, service, email: Dict, response: str) -> str:
        """Create draft in Gmail and apply review label

        Args:
            service: Gmail service object
            email: Dictionary containing email info
            response: Draft response string

        Returns:
            Draft ID
        """
        message = {
            'message': {
                'raw': base64.urlsafe_b64encode(
                    f"To: {email['from_address']}\n"
                    f"Subject: RE: {email['subject']}\n\n"
                    f"{response}".encode('utf-8')
                ).decode('utf-8')
            }
        }

        draft = service.users().drafts().create(
            userId='me',
            body=message
        ).execute()

        # Apply review label
        label_id = self.create_or_get_label_id(service, self.REVIEW_LABEL)
        service.users().messages().modify(
            userId='me',
            id=draft['message']['id'],
            body={'addLabelIds': [label_id]}
        ).execute()

        return draft['id']

    def apply_labels(self, service, msg_id: str, priority: int):
        """Applies the priority label.

        Args:
            service: The Gmail service object.
            msg_id: The message ID.
            priority: The email priority.
        """
        # Map priority to our defined labels
        priority = max(0, min(priority, 4))  # Clamp to 0-4 range
        label_name = self.PRIORITY_LABELS[priority]
        label_id = self.create_or_get_label_id(service, label_name)

        mods = {"addLabelIds": [label_id], "removeLabelIds": []}
        service.users().messages().modify(userId="me", id=msg_id, body=mods).execute()
        self.logger.info(f"Applied label '{label_name}' to message ID {msg_id}")

    def initialize_feedback_entry(self, msg_id: str, subject: str, assigned_priority: int):
        """Initializes a feedback entry in feedback.json with basic info.

        Args:
            msg_id: The message ID.
            subject: The email subject.
            assigned_priority: The assigned priority.

        Returns:
            A dictionary containing the feedback entry.
        """
        feedback_entry = {
            "msg_id": msg_id,
            "subject": subject,
            "assigned_priority": assigned_priority,
            "feedback_comments": "",  # Initialize as empty
            "suggested_priority": None,  # Initialize as None
            "add_to_topics": None,  # Initialize as None
            "add_to_source": None,  # Initialize as None
            "timestamp": None,  # Will be filled in by process_feedback.py
        }
        return feedback_entry

    def save_feedback(self, feedback_entries: List[Dict]):
        """Saves (or initializes) the feedback file.

        Args:
            feedback_entries: A list of feedback entries.
        """
        if not os.path.exists(self.FEEDBACK_FILE):
            with open(self.FEEDBACK_FILE, "w") as f:
                json.dump(feedback_entries, f, indent=4)
        else:  # file exists, read, append, and write
            with open(self.FEEDBACK_FILE, "r+") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:  # if the file exists but is empty
                    data = []
                data.extend(feedback_entries)  # add feedback
                f.seek(0)  # rewind
                json.dump(data, f, indent=4)

    def run(self):
        """Main function to process emails."""
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Process emails')
        parser.add_argument('--max-messages', type=int, default=1000,
                           help='Maximum number of messages to process (use 0 for all)')
        parser.add_argument('--generate-drafts', action='store_true',
                           help='Generate draft responses for critical emails')
        args = parser.parse_args()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        service = self.get_gmail_service()
        preferences = self.load_preferences(self.PREFERENCES_FILE)

        with open(self.EMAIL_ANALYSIS_PROMPT_FILE, "r") as f:
            analysis_prompt = f.read()

        results = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=args.max_messages)
            .execute()
        )
        messages = results.get("messages", [])

        if not messages:
            self.logger.info("No messages found.")
            return
        feedback_entries = []  # list to store feedback entries
        # Check for existing messages first
        existing_ids = {row[0] for row in self.db_conn.execute("SELECT msg_id FROM email_analyses").fetchall()}

        for message in messages:
            msg_id = message["id"]
            if msg_id in existing_ids:
                self.logger.info(f"Skipping already processed message {msg_id}")
                continue
            message_full = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            headers = message_full["payload"]["headers"]
            subject = next(
                (header["value"] for header in headers if header["name"] == "Subject"), ""
            )
            from_header = next(
                (header["value"] for header in headers if header["name"] == "From"), ""
            )

            body = self.get_message_body(service, "me", msg_id)
            if not body:
                self.logger.info(f"Skipping message {msg_id} - no body found.")
                continue
            analysis_result = self.analyze_email_with_deepinfra(
                body, subject, from_header, analysis_prompt
            )

            # Create minimal viable result if analysis failed
            if not analysis_result:
                self.logger.warning(f"Using fallback analysis for {msg_id}")
                analysis_result = {
                    "scores": {
                        "automation_score": {"score": 0.5},
                        "content_value": {"score": 0.5},
                        "human_interaction": {"score": 0.5},
                        "time_value": {"score": 0.5},
                        "business_impact": {"score": 0.5}
                    },
                    "metadata": {
                        "source": "Analysis Failed",
                        "error": True
                    }
                }

            # Calculate priority even if missing from analysis result
            if "priority" not in analysis_result:
                self.logger.info(f"Calculating priority locally for {msg_id} (missing in analysis)")
                analysis_result['priority'] = self.calculate_priority(analysis_result, preferences)

            priority = analysis_result['priority']
            self.apply_labels(service, msg_id, priority)
            self.store_analysis_result(msg_id, subject, from_header, analysis_result, priority, message_full)

            # Initialize a feedback entry and add to list
            feedback_entry = self.initialize_feedback_entry(msg_id, subject, priority)
            feedback_entries.append(feedback_entry)

        # Save feedback file
        if feedback_entries:
            self.save_feedback(feedback_entries)

        # Generate draft responses if requested
        if args.generate_drafts:
            self.logger.info("\nGenerating draft responses for critical emails...")

        # Generate draft responses if requested
        if args.generate_drafts:
            self.logger.info("\nGenerating draft responses for critical emails...")
            critical_emails = self.get_critical_emails(self.db_conn)

            for email in critical_emails:
                try:
                    self.logger.info(f"\nProcessing critical email: {email['subject']}")
                    draft_response = self.generate_draft_response(service, email)
                    draft_id = self.create_draft(service, email, draft_response)
                    self.logger.info(f"Created draft {draft_id} with label {self.REVIEW_LABEL}")
                except Exception as e:
                    self.logger.error(f"Error processing {email['msg_id']}: {str(e)}")

    def load_preferences(self, file_path: str) -> Dict:
        """Loads email preferences from a JSON file with detailed error handling.

        Args:
            file_path: The path to the preferences file.

        Returns:
            A dictionary containing the email preferences.

        Raises:
            FileNotFoundError: If the preferences file is missing.
            json.JSONDecodeError: If the preferences file contains invalid JSON.
            Exception: If an unexpected error occurs while loading the file.
        """
        full_path = os.path.abspath(os.path.expanduser(file_path))

        if not os.path.exists(full_path):
            self.logger.error(f"Error: Missing preferences file at {full_path}")
            self.logger.error("1. Create the file at this exact path")
            self.logger.error(f"2. Verify the path matches: {full_path}")
            self.logger.error("3. Use the format shown in the README.md")
            sys.exit(1)

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error: Invalid JSON in {file_path}:")
            self.logger.error(f"Line {e.lineno}: {e.msg}")
            self.logger.error(f"Fix the syntax error and try again")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error loading {file_path}: {str(e)}")
            sys.exit(1)


def main():
    """Main function."""
    classifier = EmailClassifier()
    classifier.execute()


if __name__ == "__main__":
    main()
