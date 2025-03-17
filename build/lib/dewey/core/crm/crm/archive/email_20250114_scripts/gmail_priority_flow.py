"""Gmail Priority Flow - Automated Email Prioritization System

This script provides automated email prioritization and labeling using the Gmail API
and AI-based classification. Key features include:

- Automated email prioritization (0-5 scale)
- Intelligent label application
- Contact-based priority adjustments
- Edge case detection and logging
- Performance monitoring and reporting

The system integrates with:
- Gmail API for email access and labeling
- DeepInfra API for AI-based classification
- Local SQLite database for contact management
- JSON-based configuration for custom rules

Typical usage:
1. Configure credentials and preferences
2. Run script to process emails
3. Review results and edge cases
4. Adjust preferences as needed
"""

import argparse
import json
import logging
import os
import pickle
import re
import sqlite3
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests
from dotenv import load_dotenv
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

# Configure logging
load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# Filter out the OAuth client message
class OAuthClientFilter(logging.Filter):
    def filter(self, record):
        return "file_cache is only supported with oauth2client<4.0.0" not in record.msg


# Configure logging with filter
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("gmail_priority_flow.log")],
)

# Add the filter to all handlers
for handler in logging.getLogger().handlers:
    handler.addFilter(OAuthClientFilter())

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def sanitize_email_content(email_content: str) -> str:
    """Sanitize and clean email content to improve prioritization accuracy.

    Performs the following cleaning operations:
    - Removes URLs
    - Strips HTML tags
    - Trims whitespace
    - Normalizes content for AI processing

    Args:
    ----
        email_content (str): Raw email content from Gmail API

    Returns:
    -------
        str: Cleaned email content ready for analysis

    Example:
    -------
        >>> sanitize_email_content("<p>Visit https://example.com</p>")
        'Visit'

    """
    # Remove URLs
    email_content = re.sub(r"http\S+", "", email_content)

    # Remove HTML tags if any
    email_content = re.sub(r"<[^>]+>", "", email_content)

    # Trim whitespace
    email_content = email_content.strip()

    return email_content


def prepare_email_content(subject: str, snippet: str) -> str:
    """Prepare and sanitize email content for prioritization analysis.

    Combines subject and snippet into a standardized format:
    - Prepends "Subject: " to subject line
    - Adds "Content: " before snippet
    - Applies sanitization to both components

    Args:
    ----
        subject (str): Email subject line
        snippet (str): Email content snippet from Gmail API

    Returns:
    -------
        str: Formatted and sanitized email content string

    Example:
    -------
        >>> prepare_email_content("Hello", "This is a test email")
        'Subject: Hello\n\nContent: This is a test email'

    """
    cleaned_snippet = sanitize_email_content(snippet)
    return f"Subject: {subject}\n\nContent: {cleaned_snippet}"


def load_environment_variables() -> Tuple[str, int]:
    """Load and validate required environment variables.

    Required variables:
    - DEEPINFRA_API_KEY: API key for DeepInfra service
    - DEFAULT_MAX_EMAILS: Maximum number of emails to process (default: 10)

    Returns:
    -------
        Tuple[str, int]: Tuple containing (api_key, default_max_emails)

    Raises:
    ------
        SystemExit: If required environment variables are missing

    """
    load_dotenv()
    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        logging.critical("DEEPINFRA_API_KEY is not set in the environment variables.")
        sys.exit(1)
    default_max_emails = int(os.getenv("DEFAULT_MAX_EMAILS", 10))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))
    return api_key, default_max_emails


def get_all_label_ids(service) -> Dict[str, str]:
    """Retrieve all label IDs and names from Gmail account.

    Caches label information to minimize API calls and improve performance.
    Handles API errors gracefully with logging.

    Args:
    ----
        service: Authenticated Gmail API service object

    Returns:
    -------
        Dict[str, str]: Dictionary mapping label names to their IDs

    Example:
    -------
        {
            "INBOX": "Label_1",
            "SENT": "Label_2",
            "Priority/High": "Label_3"
        }

    """
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = {label["name"]: label["id"] for label in results.get("labels", [])}
        return labels
    except Exception as e:
        logging.error(f"Error retrieving labels: {str(e)}")
        return {}


@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ValueError)),
)
def prioritize_with_deepinfra(email_content: str, api_key: str) -> Tuple[int, float]:
    """Prioritize email using DeepInfra API with retry logic.

    Uses a pre-defined system prompt to classify email importance on a 0-5 scale.
    Implements exponential backoff retry for API reliability.

    Args:
    ----
        email_content (str): Prepared email content for analysis
        api_key (str): DeepInfra API key for authentication

    Returns:
    -------
        Tuple[int, float]: Tuple containing:
            - priority (int): Priority score (0-5)
            - confidence (float): Confidence score (0.0-1.0)

    Raises:
    ------
        requests.exceptions.RequestException: On API communication failures
        ValueError: On invalid API response format

    Example:
    -------
        >>> prioritize_with_deepinfra("Subject: Test\n\nContent: Hello", "api_key")
        (3, 0.85)

    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    system_prompt = """You are an email prioritization assistant. Your task is to analyze emails and assign them a priority level from 0-5 based on the following criteria:

5 (Critical):
- All direct client communications (inquiries, responses, updates)
- Client form submissions and onboarding
- Client payment failures or declined transactions
- Server downtime or critical system alerts
- Security breaches or unauthorized access
- Legal/compliance deadlines

4 (High):
- High-value content from specified sources (Tom Brakke, AFII)
- Time-sensitive business opportunities
- Important financial documents or contracts
- System security notifications (non-breach)

3 (Business Operations):
- Payment failures and declined transactions (non-client)
- Scheduled payment confirmations and receipts
- Account status updates (non-critical)
- Meeting confirmations and calendar invites
- Business application status updates
- Standard support tickets or inquiries (non-client)
- Regular financial reports and statements
- Standard API or system notifications

2 (Low):
- Newsletter subscriptions
- Industry news and updates
- Non-urgent notifications
- General announcements
- Community updates
- Product updates (non-critical)

1 (Very Low):
- Social media notifications
- Marketing communications from known sources
- Promotional content from business partners
- System notifications (plugin updates, backups)
- General platform updates

0 (Marketing/Automated):
- Pure marketing emails
- Automated notifications
- Promotional content
- Sales and discount offers
- Mercury Bank notifications

Specific Content Rules:
1. Fort Knightley newsletters should be priority 4 (high value content)
2. Fighting ESG Pushback group emails should be priority 2 (unless directly addressed to the user)
3. Substack newsletters should be priority 1-2 (based on importance of author)
4. Marketing emails from companies (Salesforce, etc.) should always be 0
5. Meeting summaries and calendar invites should be priority 3
6. System notifications (plugin updates, backups) should be priority 1
7. Mercury Bank notifications should always be 0
8. New form entries/submissions from clients should be priority 5
9. Form entries marked as potential spam should remain priority 1

Key factors for high priority (4-5):
- ALL client communications (always priority 5)
- Time-sensitive content
- Direct requests or questions from non-clients (priority 4)
- Important business matters
- Emergency notifications
- High-value content from specified sources

Important rules:
1. Any client communication should ALWAYS be priority 5 (including payment issues)
2. Marketing emails should always be 0-1 priority
3. Group discussion emails should be max priority 2 unless directly relevant
4. Form submissions should be carefully evaluated for client vs non-client
5. Confidence score (0-100) should reflect:
   - Clarity of the classification
   - How well it matches the criteria
   - Available context

Return ONLY a JSON object with two fields:
1. 'priority': integer 0-5
2. 'confidence': float 0-1
"""

    try:
        response = requests.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers=headers,
            json={
                "model": "openchat/openchat_3.5",  # Using a smaller, faster model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Analyze this email:\n{email_content}",
                    },
                ],
                "temperature": 0.1,  # Lower temperature for more consistent results
                "max_tokens": 100,
            },
            timeout=10,
        )

        response.raise_for_status()
        result = response.json()

        if not result.get("choices"):
            logging.error("No choices in API response")
            return None, 0.0

        try:
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            priority = int(parsed["priority"])
            confidence = float(parsed["confidence"])

            if not (0 <= priority <= 5 and 0 <= confidence <= 1):
                raise ValueError("Invalid priority or confidence values")

            return priority, confidence

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logging.error(f"Error parsing API response: {str(e)}")
            return None, 0.0

    except Exception as e:
        logging.error(f"Error calling DeepInfra API: {str(e)}")
        raise


@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception),
)
def label_email(
    service, message_id: str, priority: int, label_cache: Dict[str, str]
) -> bool:
    """Apply priority and special labels to email with intelligent handling.

    Features:
    - Creates missing priority labels automatically
    - Handles meeting summary detection
    - Removes conflicting priority labels
    - Implements retry logic for reliability

    Args:
    ----
        service: Authenticated Gmail API service object
        message_id (str): Unique Gmail message ID
        priority (int): Priority level (0-5)
        label_cache (Dict[str, str]): Cache of label names to IDs

    Returns:
    -------
        bool: True if labeling succeeded, False otherwise

    Example:
    -------
        >>> label_email(service, "msg123", 3, {"Priority/Medium": "Label_1"})
        True

    """
    label_names = {
        0: "Priority/Marketing",
        1: "Priority/Very Low",
        2: "Priority/Low",
        3: "Priority/Medium",
        4: "Priority/High",
        5: "Priority/Critical",
    }

    try:
        # Get current message to check labels
        msg = service.users().messages().get(userId="me", id=message_id).execute()
        current_labels = set(msg.get("labelIds", []))

        # Get or create priority label
        label_name = label_names.get(priority)
        if not label_name:
            logging.warning(
                f"Invalid priority {priority} for message {message_id}. Skipping labeling."
            )
            return False

        label_id = label_cache.get(label_name)
        if not label_id:
            try:
                label = (
                    service.users()
                    .labels()
                    .create(userId="me", body={"name": label_name})
                    .execute()
                )
                label_id = label["id"]
                label_cache[label_name] = label_id
                logging.info(f"Created new label '{label_name}' with ID {label_id}.")
            except Exception as e:
                logging.error(f"Error creating label '{label_name}': {str(e)}")
                return False

        # Check if this is a meeting summary
        subject = next(
            (
                header["value"]
                for header in msg["payload"]["headers"]
                if header["name"].lower() == "subject"
            ),
            "",
        ).lower()

        labels_to_add = [label_id]
        labels_to_remove = []

        # Handle meeting summaries
        if any(term in subject for term in ["meeting summary", "1:1", "call summary"]):
            call_summary_label = label_cache.get("Call Summary")
            if not call_summary_label:
                try:
                    label = (
                        service.users()
                        .labels()
                        .create(userId="me", body={"name": "Call Summary"})
                        .execute()
                    )
                    call_summary_label = label["id"]
                    label_cache["Call Summary"] = call_summary_label
                except Exception:
                    pass
            if call_summary_label:
                labels_to_add.append(call_summary_label)

        # Remove existing priority labels
        for existing_label in current_labels:
            label_name = next(
                (
                    name
                    for name, id_ in label_cache.items()
                    if id_ == existing_label and name.startswith("Priority/")
                ),
                None,
            )
            if label_name and label_name != label_names[priority]:
                labels_to_remove.append(existing_label)

        # Apply labels
        if labels_to_remove:
            service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": labels_to_remove}
            ).execute()

        service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": labels_to_add}
        ).execute()

        return True

    except Exception as e:
        logging.error(f"Error labeling email {message_id}: {str(e)}")
        return False


def fetch_emails(service, max_results: int = 10) -> List[Dict]:
    """Fetch emails from inbox that haven't been priority-labeled yet.

    Implements pagination to handle large email volumes efficiently.
    Filters emails using a comprehensive query to exclude already processed messages.

    Args:
    ----
        service: Authenticated Gmail API service object
        max_results (int): Maximum number of emails to fetch (default: 10)

    Returns:
    -------
        List[Dict]: List of email dictionaries containing:
            - id: Message ID
            - snippet: Email content snippet
            - subject: Email subject
            - from_email: Sender email address
            - to_address: Recipient email address
            - labels: Current labels
            - date: Email date

    Example:
    -------
        [{
            "id": "msg123",
            "snippet": "This is a test email...",
            "subject": "Test Email",
            "from_email": "test@example.com",
            "to_address": "user@example.com",
            "labels": ["INBOX"],
            "date": datetime(2023, 1, 1)
        }]

    """
    query = (
        "(label:inbox OR label:sent) -label:Priority/Marketing -label:Priority/Very Low -label:Priority/Low \
             -label:Priority/Medium -label:Priority/High -label:Priority/Critical \
             after:2023/11/01"
    )

    try:
        logging.info(f"Executing Gmail query: {query}")
        messages = []
        earliest_date = None
        latest_date = None
        next_page_token = None
        total_fetched = 0
        page_count = 0

        while total_fetched < max_results:
            page_count += 1
            logging.info(
                f"Fetching page {page_count} (total emails so far: {total_fetched})"
            )
            # Get next batch of messages
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    pageToken=next_page_token,
                    maxResults=min(
                        500, max_results - total_fetched
                    ),  # Gmail API max per page is 500
                )
                .execute()
            )

            batch_size = len(results.get("messages", []))
            logging.info(f"Found {batch_size} emails on page {page_count}")

            if not results.get("messages"):
                logging.info("No more emails found matching the criteria")
                break

            for message in results.get("messages", []):
                if total_fetched >= max_results:
                    break

                try:
                    logging.debug(f"Fetching details for message {message['id']}")
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message["id"])
                        .execute()
                    )

                    # Extract internal date (epoch milliseconds)
                    internal_date = (
                        int(msg.get("internalDate", 0)) / 1000
                    )  # Convert to seconds
                    date = datetime.fromtimestamp(internal_date)

                    if not earliest_date or date < earliest_date:
                        earliest_date = date
                        logging.info(
                            f"New earliest date found: {earliest_date.strftime('%Y-%m-%d')}"
                        )
                    if not latest_date or date > latest_date:
                        latest_date = date
                        logging.info(
                            f"New latest date found: {latest_date.strftime('%Y-%m-%d')}"
                        )

                    messages.append(
                        {
                            "id": message["id"],
                            "snippet": msg.get("snippet", ""),
                            "subject": next(
                                (
                                    header["value"]
                                    for header in msg["payload"]["headers"]
                                    if header["name"].lower() == "subject"
                                ),
                                "No Subject",
                            ),
                            "from_email": next(
                                (
                                    header["value"]
                                    for header in msg["payload"]["headers"]
                                    if header["name"].lower() == "from"
                                ),
                                "Unknown",
                            ),
                            "to_address": next(
                                (
                                    header["value"]
                                    for header in msg["payload"]["headers"]
                                    if header["name"].lower() == "to"
                                ),
                                "Unknown",
                            ),
                            "labels": msg.get("labelIds", []),
                            "date": date,
                        }
                    )
                    total_fetched += 1

                    if total_fetched % 50 == 0:
                        logging.info(f"Processed {total_fetched} emails so far")

                except Exception as e:
                    # Check if this is a precondition failure (email modified/deleted)
                    if "failedPrecondition" in str(e):
                        logging.debug(
                            f"Skipping modified/deleted email {message['id']}"
                        )
                    else:
                        logging.error(f"Error fetching email {message['id']}: {str(e)}")
                    continue

            # Get next page token
            next_page_token = results.get("nextPageToken")
            if not next_page_token:
                logging.info("No more pages available")
                break
            logging.info("Moving to next page")

        if earliest_date and latest_date:
            logging.info(
                f"\nProcessing emails from {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}"
            )
            logging.info(f"Total emails found: {total_fetched}")

        return messages
    except Exception as e:
        logging.error(f"Error fetching email list: {str(e)}")
        return []


def authenticate_gmail() -> any:
    """Authenticate with Gmail API using OAuth2 flow.

    Handles both initial authentication and token refresh scenarios.
    Stores credentials in a pickle file for future use.

    Returns:
    -------
        any: Authenticated Gmail API service object

    Raises:
    ------
        SystemExit: If authentication fails
        GoogleAuthError: On authentication errors
        FileNotFoundError: If credentials file is missing

    Example:
    -------
        >>> service = authenticate_gmail()
        >>> service.users().labels().list(userId='me').execute()

    """
    token_pickle = "scripts/token.pickle"
    credentials_path = "scripts/credentials.json"

    try:
        logging.info("Initializing Gmail API connection...")
        # Try to load saved credentials
        if os.path.exists(token_pickle):
            logging.info("Loading saved credentials...")
            with open(token_pickle, "rb") as token:
                creds = pickle.load(token)
        else:
            logging.info(
                "No saved credentials found. Starting new authentication flow..."
            )
            creds = None

        # Check if credentials are valid
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logging.info("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                logging.info("Starting local authentication server...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            logging.info("Saving credentials for future use...")
            with open(token_pickle, "wb") as token:
                pickle.dump(creds, token)

        logging.info("Building Gmail service...")
        service = build("gmail", "v1", credentials=creds)
        logging.info("Gmail API connection established successfully.")
        return service

    except (FileNotFoundError, GoogleAuthError) as e:
        logging.error(f"Authentication failed: {str(e)}")
        logging.info(
            f"Please ensure {credentials_path} is in the correct location and is valid."
        )
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during authentication: {str(e)}")
        sys.exit(1)


def log_edge_case(case_data: Dict):
    """Log edge cases to a structured JSON file for analysis.

    Edge cases include:
    - Low confidence classifications
    - Labeling failures
    - Prioritization errors
    - Processing exceptions

    Args:
    ----
        case_data (Dict): Dictionary containing edge case details including:
            - type: Edge case type
            - subject: Email subject
            - priority: Assigned priority
            - confidence: Classification confidence
            - reason: Description of issue
            - date: Timestamp of occurrence

    Example:
    -------
        >>> log_edge_case({
            "type": "low_confidence",
            "subject": "Test Email",
            "priority": 3,
            "confidence": 0.65,
            "reason": "Ambiguous content",
            "date": "2023-01-01T12:00:00"
        })

    """
    edge_case = {"timestamp": datetime.now().isoformat(), **case_data}

    try:
        # Append to edge cases log file
        with open("edge_cases.json", "a+") as f:
            f.write(json.dumps(edge_case) + "\n")
    except Exception as e:
        logging.error(f"Failed to log edge case: {str(e)}")


def summarize_results(processed_emails: List[Dict]):
    """Generate comprehensive summary of email processing results.

    Provides:
    - Overall statistics
    - Priority distribution
    - Sender-based analysis
    - Systematic issue detection
    - Performance metrics

    Args:
    ----
        processed_emails (List[Dict]): List of processed email dictionaries containing:
            - subject: Email subject
            - priority: Final priority
            - initial_priority: Initial AI priority
            - confidence: Classification confidence
            - adjustment_reason: Reason for priority adjustment
            - id: Message ID
            - date: Email date

    Example Output:
        === Email Processing Summary ===
        Date Range: 2023-01-01 to 2023-01-31
        Total emails processed: 1000
        Successfully labeled: 950
        Failed: 50
        Time taken: 120.50 seconds

    """
    priority_groups = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
    sender_groups = {}  # Track priorities by sender

    # Track date ranges
    earliest_date = None
    latest_date = None

    for email in processed_emails:
        priority_groups[email["priority"]].append(email["subject"])

        # Track date range
        date = email.get("date")
        if date:
            if not earliest_date or date < earliest_date:
                earliest_date = date
            if not latest_date or date > latest_date:
                latest_date = date

        # Extract sender from subject patterns
        sender = "Unknown"
        subject = email["subject"].lower()

        # Identify common senders/types
        if "fort knightley" in subject:
            sender = "Fort Knightley Newsletter"
        elif "[fighting-esg-pushback]" in subject:
            sender = "Fighting ESG Pushback"
        elif "[ethical capital]" in subject:
            sender = "Ethical Capital"
        elif "meeting summary" in subject or "1:1" in subject:
            sender = "Meeting Summaries"
        elif "salesforce" in subject:
            sender = "Salesforce Marketing"
        elif "mercury" in subject:
            sender = "Mercury Bank"

        if sender not in sender_groups:
            sender_groups[sender] = {"emails": [], "priorities": [], "dates": []}
        sender_groups[sender]["emails"].append(email["subject"])
        sender_groups[sender]["priorities"].append(email["priority"])
        if date:
            sender_groups[sender]["dates"].append(date)

        # Log potential edge cases
        if email["confidence"] < 0.7:
            log_edge_case(
                {
                    "type": "low_confidence",
                    "subject": email["subject"],
                    "priority": email["priority"],
                    "confidence": email["confidence"],
                    "reason": "Low confidence score",
                    "date": date.isoformat() if date else None,
                }
            )

    logging.info("\n=== Email Processing Summary ===")
    if earliest_date and latest_date:
        logging.info(
            f"Date Range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}"
        )
    logging.info(f"Total emails processed: {len(processed_emails)}")

    # Priority summary
    for priority, emails in priority_groups.items():
        if emails:
            logging.info(f"\nPriority {priority} ({len(emails)} emails):")
            for subject in emails[:3]:
                logging.info(f"  - {subject}")

    # Sender-based analysis
    logging.info("\n=== Sender Analysis ===")
    for sender, data in sender_groups.items():
        if data["emails"]:
            avg_priority = sum(data["priorities"]) / len(data["priorities"])
            logging.info(f"\n{sender}:")
            logging.info(f"  Average Priority: {avg_priority:.1f}")
            logging.info(f"  Email Count: {len(data['emails'])}")
            if data["dates"]:
                sender_earliest = min(data["dates"])
                sender_latest = max(data["dates"])
                logging.info(
                    f"  Date Range: {sender_earliest.strftime('%Y-%m-%d')} to {sender_latest.strftime('%Y-%m-%d')}"
                )
            logging.info("  Recent Examples:")
            for subject in data["emails"][-3:]:
                logging.info(f"    - {subject}")

    # Identify systematic issues
    logging.info("\n=== Potential Systematic Issues ===")

    # Check Fort Knightley priority
    fort_knightley = sender_groups.get("Fort Knightley Newsletter", {"priorities": []})
    if fort_knightley["priorities"] and any(
        p < 4 for p in fort_knightley["priorities"]
    ):
        logging.info("  - Fort Knightley newsletters might be under-prioritized")

    # Check Fighting ESG Pushback priority
    esg = sender_groups.get("Fighting ESG Pushback", {"priorities": []})
    if esg["priorities"] and any(p > 2 for p in esg["priorities"]):
        logging.info("  - Fighting ESG Pushback emails might be over-prioritized")

    # Check marketing emails
    marketing = sender_groups.get("Salesforce Marketing", {"priorities": []})
    if marketing["priorities"] and any(p > 0 for p in marketing["priorities"]):
        logging.info("  - Marketing emails might be over-prioritized")

    # Check Mercury Bank notifications
    mercury = sender_groups.get("Mercury Bank", {"priorities": []})
    if mercury["priorities"] and any(p > 0 for p in mercury["priorities"]):
        logging.info("  - Mercury Bank notifications might be over-prioritized")


def load_preferences() -> Dict:
    """Load email prioritization preferences from JSON config file.

    The preferences file contains:
    - High priority sources and keywords
    - Low priority sources and keywords
    - Newsletter defaults
    - Override rules

    Returns:
    -------
        Dict: Dictionary containing prioritization preferences

    Example:
    -------
        {
            "high_priority_sources": [
                {
                    "keywords": ["urgent", "important"],
                    "min_priority": 4,
                    "reason": "Contains urgent keywords"
                }
            ],
            "low_priority_sources": [
                {
                    "keywords": ["newsletter", "promotion"],
                    "max_priority": 1,
                    "reason": "Marketing content"
                }
            ]
        }

    """
    try:
        with open("scripts/email_preferences.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Could not load preferences: {str(e)}. Using defaults.")
        return {}


def check_contact_priority(from_email: str) -> Tuple[int, str]:
    """Check contact database for sender priority and update contact information.

    Performs both exact email and name-based matching.
    Updates contact database with new senders.

    Args:
    ----
        from_email (str): Sender email address in "Name <email>" format

    Returns:
    -------
        Tuple[int, str]: Tuple containing:
            - priority (int): Contact priority if found, else None
            - reason (str): Explanation of priority determination

    Example:
    -------
        >>> check_contact_priority("John Doe <john@example.com>")
        (4, "Known contact: John Doe (priority 4)")

    """
    try:
        conn = sqlite3.connect("email_data.db")
        cursor = conn.cursor()

        # Extract name and email from "Name <email>" format
        email_match = re.search(r"<(.+?)>", from_email)
        name_match = re.search(r"^([^<]+)", from_email)

        clean_email = email_match.group(1) if email_match else from_email
        display_name = name_match.group(1).strip() if name_match else None

        # Try exact email match first
        cursor.execute(
            "SELECT email, name, priority FROM contacts WHERE email = ?", (clean_email,)
        )
        result = cursor.fetchone()

        # If no match and we have a name, try name match
        if not result and display_name:
            cursor.execute(
                "SELECT email, name, priority FROM contacts WHERE name LIKE ?",
                (f"%{display_name}%",),
            )
            result = cursor.fetchone()

        if result:
            contact_email, contact_name, priority = result
            return (
                priority,
                f"Known contact: {contact_name or contact_email} (priority {priority})",
            )

        # Track new contact for future analysis
        cursor.execute(
            """
            INSERT OR IGNORE INTO contacts
            (email, name, domain, email_count, last_seen)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        """,
            (
                clean_email,
                display_name,
                clean_email.split("@")[1] if "@" in clean_email else None,
            ),
        )

        conn.commit()
        conn.close()
        return None, "Contact not found"

    except Exception as e:
        logging.error(f"Error checking contacts database: {str(e)}")
        return None, f"Database error: {str(e)}"


def adjust_priority_based_on_preferences(
    email_content: str, initial_priority: int, preferences: Dict, from_email: str
) -> Tuple[int, str]:
    """Adjust email priority based on user preferences and contact information.

    Implements a multi-stage adjustment process:
    1. Check contact database for sender-specific priority
    2. Apply high-priority source rules
    3. Apply low-priority source rules
    4. Apply newsletter defaults
    5. Apply override rules

    Args:
    ----
        email_content (str): Prepared email content
        initial_priority (int): AI-generated priority score
        preferences (Dict): Loaded preferences dictionary
        from_email (str): Sender email address

    Returns:
    -------
        Tuple[int, str]: Tuple containing:
            - adjusted_priority (int): Final priority score
            - reason (str): Explanation of adjustment

    Example:
    -------
        >>> adjust_priority_based_on_preferences(
            "Subject: Urgent\n\nContent: Please review",
            3,
            preferences,
            "john@example.com"
        )
        (4, "Adjusted up: Contains urgent keywords")

    """
    # First check contacts database
    contact_priority, reason = check_contact_priority(from_email)
    if contact_priority is not None and contact_priority > initial_priority:
        return contact_priority, reason

    content_lower = email_content.lower()

    # Check high priority sources
    for source in preferences.get("high_priority_sources", []):
        if any(keyword.lower() in content_lower for keyword in source["keywords"]):
            if initial_priority < source["min_priority"]:
                return source["min_priority"], f"Adjusted up: {source['reason']}"

    # Check low priority sources
    for source in preferences.get("low_priority_sources", []):
        if any(keyword.lower() in content_lower for keyword in source["keywords"]):
            if "priority" in source:
                return source["priority"], f"Override: {source['reason']}"
            elif initial_priority > source["max_priority"]:
                return source["max_priority"], f"Adjusted down: {source['reason']}"

    # Apply newsletter defaults
    for newsletter_type, config in preferences.get("newsletter_defaults", {}).items():
        if any(keyword.lower() in content_lower for keyword in config["keywords"]):
            return config["default_priority"], f"Newsletter default: {config['reason']}"

    # Check override rules
    for rule in preferences.get("override_rules", []):
        if any(keyword.lower() in content_lower for keyword in rule["keywords"]):
            if initial_priority < rule["min_priority"]:
                return rule["min_priority"], f"Rule override: {rule['reason']}"

    return initial_priority, "No adjustment needed"


def main():
    """Main function to prioritize Gmail inbox.

    Orchestrates the entire email processing workflow:
    1. Loads configuration and authenticates with Gmail
    2. Fetches unprocessed emails
    3. Processes each email through prioritization pipeline
    4. Applies labels based on priority
    5. Generates summary reports
    6. Handles errors and edge cases

    Command-line arguments:
    --max-emails: Maximum number of emails to process (default: 5000)

    Example usage:
        python gmail_priority_flow.py --max-emails 1000
    """
    logging.info("Starting email prioritization process...")
    logging.info("Loading environment variables and preferences...")
    api_key, default_max_emails = load_environment_variables()
    preferences = load_preferences()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Prioritize Gmail inbox")
    parser.add_argument(
        "--max-emails",
        type=int,
        default=5000,
        help="Maximum number of emails to process (default: 5000)",
    )
    args = parser.parse_args()

    # Initialize counters
    processed = 0
    successful = 0
    failed = 0
    start_time = time.time()

    try:
        service = authenticate_gmail()
        logging.info("Fetching Gmail labels...")
        label_cache = get_all_label_ids(service)
        logging.info("Searching for unprocessed emails...")
        messages = fetch_emails(service, args.max_emails)

        processed_emails = []

        if not messages:
            logging.info("No new emails found to process.")
            return

        logging.info(f"Found {len(messages)} emails to process.")

        for message in tqdm(messages, desc="Processing Emails"):
            processed += 1
            prepared_content = prepare_email_content(
                message["subject"], message["snippet"]
            )
            try:
                initial_priority, confidence = prioritize_with_deepinfra(
                    prepared_content, api_key
                )

                if initial_priority is not None:
                    # Adjust priority based on preferences
                    adjusted_priority, reason = adjust_priority_based_on_preferences(
                        prepared_content,
                        initial_priority,
                        preferences,
                        message["from_email"],
                    )

                    if adjusted_priority != initial_priority:
                        logging.info(
                            f"Priority adjusted for '{message['subject']}': {initial_priority} -> {adjusted_priority} ({reason})"
                        )

                    if label_email(
                        service, message["id"], adjusted_priority, label_cache
                    ):
                        successful += 1
                        processed_emails.append(
                            {
                                "subject": message["subject"],
                                "priority": adjusted_priority,
                                "initial_priority": initial_priority,
                                "confidence": confidence,
                                "adjustment_reason": reason,
                                "id": message["id"],
                                "date": message.get("date"),
                            }
                        )
                        # Include date in logging
                        date_str = (
                            message.get("date").strftime("%Y-%m-%d")
                            if message.get("date")
                            else "Unknown Date"
                        )
                        logging.info(
                            f"Processed email [{date_str}]: {message['subject']} - Priority: {adjusted_priority} (Initial: {initial_priority}, Confidence: {confidence:.2f})"
                        )
                    else:
                        failed += 1
                        logging.warning(f"Failed to label email: {message['subject']}")
                        log_edge_case(
                            {
                                "type": "labeling_failure",
                                "subject": message["subject"],
                                "priority": adjusted_priority,
                                "initial_priority": initial_priority,
                                "confidence": confidence,
                                "reason": "Failed to apply label",
                                "date": (
                                    message.get("date").isoformat()
                                    if message.get("date")
                                    else None
                                ),
                            }
                        )
                else:
                    failed += 1
                    logging.warning(
                        f"Skipped labeling due to prioritization error: {message['subject']}"
                    )
                    log_edge_case(
                        {
                            "type": "prioritization_failure",
                            "subject": message["subject"],
                            "reason": "Failed to determine priority",
                            "date": (
                                message.get("date").isoformat()
                                if message.get("date")
                                else None
                            ),
                        }
                    )
            except Exception as e:
                failed += 1
                logging.error(
                    f"Error processing email: {message['subject']} - {str(e)}"
                )
                log_edge_case(
                    {
                        "type": "processing_error",
                        "subject": message["subject"],
                        "error": str(e),
                        "reason": "Exception during processing",
                        "date": (
                            message.get("date").isoformat()
                            if message.get("date")
                            else None
                        ),
                    }
                )
                continue

        end_time = time.time()
        elapsed_time = end_time - start_time

        logging.info("\nSummary:")
        logging.info(f"Total emails processed: {processed}")
        logging.info(f"Successfully labeled: {successful}")
        logging.info(f"Failed: {failed}")
        logging.info(f"Time taken: {elapsed_time:.2f} seconds")

        summarize_results(processed_emails)

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {str(e)}")
        log_edge_case(
            {
                "type": "critical_error",
                "error": str(e),
                "reason": "Critical system error",
            }
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
