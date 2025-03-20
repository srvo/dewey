#!/usr/bin/env python3
"""Email classifier for Gmail using Deepinfra API for prioritization."""
#TODO move output directory to ~/input_data
import os
import sys
import json
import base64
import argparse
import time
from typing import Dict, List
from dotenv import load_dotenv
import duckdb
from datetime import datetime, timezone
import logging
from dewey.core.base_script import BaseScript

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.expanduser("~"), "crm", ".env"))

# DuckDB setup with connection pooling and retries
output_dir = "/Users/srvo/input_data/ActiveData"
os.makedirs(output_dir, exist_ok=True)  # Ensure directory exists

def get_db_connection():
    """Get a DuckDB connection with retry logic and connection pool"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = duckdb.connect(
                database=f'{output_dir}/email_classifier.duckdb',
                read_only=False,
                config={
                    'access_mode': 'READ_WRITE',
                    'threads': 1,  # Changed to integer
                    'checkpoint': 'disable',
                    'wal_autocheckpoint': '0',
                    'memory_limit': '1GB'
                }
            )
            conn.execute("PRAGMA journal_mode=WAL")  # Use WAL mode for better concurrency
            return conn
        except duckdb.IOException as e:
            if "lock" in str(e).lower() and attempt < max_retries - 1:
                print(f"Database locked, retrying ({attempt+1}/{max_retries})...")
                time.sleep(0.5 * (attempt + 1))
                continue
            raise

# Create a module-level connection for reuse
conn = get_db_connection()
conn.execute("""
    CREATE TABLE IF NOT EXISTS email_analyses (
        msg_id VARCHAR PRIMARY KEY,
        thread_id VARCHAR,
        subject VARCHAR,
        from_address VARCHAR,
        analysis_date TIMESTAMP,
        raw_analysis JSON,
        automation_score FLOAT,
        content_value FLOAT,
        human_interaction FLOAT,
        time_value FLOAT,
        business_impact FLOAT,
        uncertainty_score FLOAT,
        metadata JSON,
        priority INTEGER,
        -- New fields from Message resource
        label_ids JSON,
        snippet TEXT,
        internal_date BIGINT,
        size_estimate INTEGER,
        -- MessagePart details
        message_parts JSON,
        -- Draft-related fields
        draft_id VARCHAR,
        draft_message JSON,
        -- Attachment info
        attachments JSON
    )
""")

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow  # pylint: disable=unused-import
import google.auth.exceptions
import google.auth.transport.requests
from openai import OpenAI
import requests
import logging
from dewey.core.base_script import BaseScript

print(f"Python version: {sys.version}")

# --- Configuration ---
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
PREFERENCES_FILE = "email_preferences.json"
DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")
EMAIL_ANALYSIS_PROMPT_FILE = "email_analysis.txt"
FEEDBACK_FILE = "/Users/srvo/lake/read/feedback.json"
FEEDBACK_INTERVAL = (
    300  # seconds (no longer used directly, but kept for potential future use)
)


def load_preferences(file_path: str) -> Dict:
    """Loads email preferences from a JSON file with detailed error handling."""
    full_path = os.path.abspath(os.path.expanduser(file_path))
    
    if not os.path.exists(full_path):
        print(f"Error: Missing preferences file at {full_path}")
        print("1. Create the file at this exact path")
        print(f"2. Verify the path matches: {full_path}")
        print("3. Use the format shown in the README.md")
        sys.exit(1)
        
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}:")
        print(f"Line {e.lineno}: {e.msg}")
        print(f"Fix the syntax error and try again")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading {file_path}: {str(e)}")
        sys.exit(1)


def get_gmail_service():
    """Authenticates with the Gmail API and returns the service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(google.auth.transport.requests.Request())
            except google.auth.exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                print("Deleting token file and re-authenticating...")
                os.remove(TOKEN_FILE)
                return get_gmail_service()
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def get_message_body(service, user_id, msg_id):
    """Retrieves the full message body."""
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
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8", "ignore"
                        )
                        break
                    elif part["mimeType"] == "text/plain" and not body:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8", "ignore"
                        )
            return body
        elif "body" in payload and "data" in payload["body"]:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                "utf-8", "ignore"
            )

        return ""

    except HttpError as error:
        print(f"An error occurred: {error}")
        return ""

def analyze_email_with_deepinfra(
    message_body: str, subject: str, from_header: str, prompt: str
) -> dict:
    """Analyzes email content using the DeepInfra API."""
    # Initialize OpenAI client with DeepInfra configuration
    # Validate API configuration before making requests
    if not os.environ.get("DEEPINFRA_API_KEY"):
        raise ValueError(
            "DEEPINFRA_API_KEY environment variable not set.\n"
            "1. Check your ~/crm/.env file exists\n"
            "2. Verify it contains: DEEPINFRA_API_KEY=your_api_key_here"
        )

    client = OpenAI(
        base_url=os.environ.get("DEEPINFRA_API_ENDPOINT", "https://api.deepinfra.com/v1/openai"),
        api_key=os.environ.get("DEEPINFRA_API_KEY", "")
    )

    try:
        chat_completion = client.chat.completions.create(
            model=os.environ.get("DEEPINFRA_MODEL", "microsoft/Phi-4-multimodal-instruct"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that responds with valid JSON"},
                {
                    "role": "user",
                    "content": f"{prompt}\n\nEmail Content:\nSubject: {subject}\nFrom: {from_header}\nBody: {message_body}"
                }
            ],
            max_tokens=500,
            temperature=0.7,
            response_format={"type": "json_object"}  # Request structured JSON output
        )

        if chat_completion.choices:
            generated_text = chat_completion.choices[0].message.content
            # First clean up API response - sometimes comes wrapped in markdown code blocks
            clean_text = generated_text.replace('```json', '').replace('```', '').strip()

            try:
                result = json.loads(clean_text)
                # Validate required structure
                if not all(key in result for key in ('scores', 'metadata')):
                    raise ValueError("Missing required 'scores' or 'metadata' fields")

                # Validate and normalize scoring values
                for category in ['scores', 'metadata']:
                    if category not in result:
                        print(f"Validation error: Missing {category} section")
                        return {}

                # Add debug logging of valid result
                print(f"🔍 Analysis results for message:")
                print(f"   Priority: {result.get('priority', 'N/A')}")
                print(f"   Scores: { {k: v['score'] for k, v in result['scores'].items()} }")
                print(f"   Source: {result['metadata'].get('source', 'Unknown')}")

                return result

            except json.JSONDecodeError as e:
                print(f"JSON Parse Error: {str(e)}")
                print("Received response content:")
                print("-" * 40)
                print(clean_text)
                print("-" * 40)
                return {}
            except Exception as e:
                print(f"Validation Error: {str(e)}")
                print("Problematic analysis result:")
                print("-" * 40)
                print(clean_text)
                print("-" * 40)
                return {}

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"HTTP Status: {e.response.status_code}")
            print(f"Response Body: {e.response.text[:200]}...")  # Show first 200 chars
        return {}
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return {}


def extract_message_parts(payload: Dict) -> List[Dict]:
    """Recursively extract message parts from payload."""
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

def extract_attachments(payload: Dict) -> List[Dict]:
    """Extract attachment information from message parts."""
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

def _calculate_uncertainty(scores: Dict) -> float:
    """Calculate uncertainty as coefficient of variation of scores."""
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

def calculate_priority(analysis_result: Dict, preferences: Dict) -> int:
    """Calculates email priority."""
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


def create_or_get_label_id(service, label_name: str) -> str:
    """Creates/gets a label ID."""
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


def store_analysis_result(msg_id: str, subject: str, from_address: str, analysis_result: dict, priority: int, message_full: dict):
    """Stores analysis results in DuckDB using batch insertion."""
    try:
        # Get fresh connection from pool
        with get_db_connection().cursor() as cursor:  # Use context manager
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
                float(_calculate_uncertainty(analysis_result.get('scores', {}))),
                json.dumps(analysis_result.get('metadata', {})),
                int(priority),
                json.dumps(message_full.get('labelIds', [])),
                message_full.get('snippet', ''),
                int(message_full.get('internalDate', 0)),
                int(message_full.get('sizeEstimate', 0)),
                json.dumps(extract_message_parts(message_full.get('payload', {}))),
                message_full.get('draftId'),  # NULL as None is handled automatically
                json.dumps(message_full.get('draftMessage')) if message_full.get('draftMessage') else None,
                json.dumps(extract_attachments(message_full.get('payload', {})))
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
            
        print(f"Successfully stored analysis for {msg_id} in DuckDB")
    except duckdb.Error as e:
        print(f"Database error storing analysis: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error storing analysis: {str(e)}")
        raise

PRIORITY_LABELS = {
    4: "Priority/Critical",
    3: "Priority/High",
    2: "Priority/Medium",
    1: "Priority/Low",
    0: "Priority/Very Low"
}

REVIEW_LABEL = "1_For_Review"

def get_critical_emails(conn, limit: int = 10) -> List[Dict]:
    """Retrieve critical priority emails from database"""
    result = conn.execute("""
        SELECT msg_id, subject, snippet, from_address 
        FROM email_analyses 
        WHERE priority = 4 
        ORDER BY analysis_date DESC 
        LIMIT ?
    """, [limit]).fetchall()
    
    columns = [col[0] for col in conn.description]
    return [dict(zip(columns, row)) for row in result]

def generate_draft_response(service, email: Dict) -> str:
    """Generate draft response using Hermes-3-Llama-3.1-405B model"""
    client = OpenAI(
        base_url="https://api.deepinfra.com/v1/openai",
        api_key=DEEPINFRA_API_KEY
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

def create_draft(service, email: Dict, response: str) -> str:
    """Create draft in Gmail and apply review label"""
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
    label_id = create_or_get_label_id(service, REVIEW_LABEL)
    service.users().messages().modify(
        userId='me',
        id=draft['message']['id'],
        body={'addLabelIds': [label_id]}
    ).execute()
    
    return draft['id']

def apply_labels(service, msg_id: str, priority: int):
    """Applies the priority label."""
    # Map priority to our defined labels
    priority = max(0, min(priority, 4))  # Clamp to 0-4 range
    label_name = PRIORITY_LABELS[priority]
    label_id = create_or_get_label_id(service, label_name)

    mods = {"addLabelIds": [label_id], "removeLabelIds": []}
    service.users().messages().modify(userId="me", id=msg_id, body=mods).execute()
    print(f"Applied label '{label_name}' to message ID {msg_id}")


def initialize_feedback_entry(msg_id: str, subject: str, assigned_priority: int):
    """Initializes a feedback entry in feedback.json with basic info."""
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


def save_feedback(feedback_entries: List[Dict]):
    """Saves (or initializes) the feedback file."""

    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(feedback_entries, f, indent=4)
    else:  # file exists, read, append, and write
        with open(FEEDBACK_FILE, "r+") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:  # if the file exists but is empty
                data = []
            data.extend(feedback_entries)  # add feedback
            f.seek(0)  # rewind
            json.dump(data, f, indent=4)


def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process emails')
    parser.add_argument('--max-messages', type=int, default=1000,
                       help='Maximum number of messages to process (use 0 for all)')
    parser.add_argument('--generate-drafts', action='store_true',
                       help='Generate draft responses for critical emails')
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs("/Users/srvo/input_data/ActiveData", exist_ok=True)
    service = get_gmail_service()
    preferences = load_preferences(PREFERENCES_FILE)

    with open(EMAIL_ANALYSIS_PROMPT_FILE, "r") as f:
        analysis_prompt = f.read()

    results = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=args.max_messages)
        .execute()
    )
    messages = results.get("messages", [])

    if not messages:
        print("No messages found.")
        return
    feedback_entries = []  # list to store feedback entries
    # Check for existing messages first
    existing_ids = {row[0] for row in conn.execute("SELECT msg_id FROM email_analyses").fetchall()}

    for message in messages:
        msg_id = message["id"]
        if msg_id in existing_ids:
            print(f"Skipping already processed message {msg_id}")
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

        body = get_message_body(service, "me", msg_id)
        if not body:
            print(f"Skipping message {msg_id} - no body found.")
            continue
        analysis_result = analyze_email_with_deepinfra(
            body, subject, from_header, analysis_prompt
        )

        # Create minimal viable result if analysis failed
        if not analysis_result:
            print(f"Using fallback analysis for {msg_id}")
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
            print(f"Calculating priority locally for {msg_id} (missing in analysis)")
            #TODO move output directory to ~/input_data
            analysis_result['priority'] = calculate_priority(analysis_result, preferences)

        priority = analysis_result['priority']
        apply_labels(service, msg_id, priority)
        store_analysis_result(msg_id, subject, from_header, analysis_result, priority, message_full)

        # Initialize a feedback entry and add to list
        feedback_entry = initialize_feedback_entry(msg_id, subject, priority)
        feedback_entries.append(feedback_entry)

    # Save feedback file
    if feedback_entries:
        save_feedback(feedback_entries)

    # Generate draft responses if requested
    if args.generate_drafts:
        print("\nGenerating draft responses for critical emails...")

    # Generate draft responses if requested
    if args.generate_drafts:
        print("\nGenerating draft responses for critical emails...")
        critical_emails = get_critical_emails(conn)
        
        for email in critical_emails:
            try:
                print(f"\nProcessing critical email: {email['subject']}")
                draft_response = generate_draft_response(service, email)
                draft_id = create_draft(service, email, draft_response)
                print(f"Created draft {draft_id} with label {REVIEW_LABEL}")
            except Exception as e:
                print(f"Error processing {email['msg_id']}: {str(e)}")


if __name__ == "__main__":
    main()