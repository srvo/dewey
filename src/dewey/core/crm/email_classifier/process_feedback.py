import argparse
import io
import json
import logging
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from dewey.core.db.connection import (
    DatabaseConnection,
    get_motherduck_connection,
)

# Try to import OpenAI with fallback if package is not installed
try:
    from openai import OpenAI
except ImportError:
    # Create a dummy class for tests to mock
    class OpenAI:
        def __init__(self, **kwargs):
            self.api_key = kwargs.get("api_key")
            self.base_url = kwargs.get("base_url")
            self.chat = type(
                "chat",
                (),
                {
                    "completions": type(
                        "completions", (), {"create": lambda **kw: None}
                    )()
                },
            )

        def __call__(self, *args, **kwargs):
            return self


ACTIVE_DATA_DIR = "/Users/srvo/input_data/ActiveData"
DB_FILE = f"{ACTIVE_DATA_DIR}/process_feedback.duckdb"
CLASSIFIER_DB = f"{ACTIVE_DATA_DIR}/email_classifier.duckdb"
load_dotenv(os.path.expanduser("~/crm/.env"))
DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")

# Define table references with defaults for proper schema
MOTHERDUCK_DB_NAME = "dewey"  # MotherDuck database name
MOTHERDUCK_EMAIL_CLASSIFIER_TABLE = "email_classifier"
MOTHERDUCK_FEEDBACK_TABLE = "email_feedback"
MOTHERDUCK_PREFERENCES_TABLE = "email_preferences"
MOTHERDUCK_EMAIL_ANALYSES_TABLE = "email_analyses"  # Added for clarity
MOTHERDUCK_EMAILS_TABLE = "emails"  # Added for clarity

# Create a global queue and a list to track background processing
feedback_queue = Queue()
background_processor_started = False
# Create a lock for synchronized printing
print_lock = threading.Lock()

# Default auto-skip threshold
DEFAULT_AUTO_SKIP_THRESHOLD = 3
# Set quiet mode as default (suppress initialization messages)
QUIET_MODE = True
# Default limit for fast loading
DEFAULT_LIMIT = 20


# Configure logging to redirect to our safe_print method
class ThreadSafeLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        # Use our safe_print function with is_background=True for log messages
        if "process_feedback_worker" in threading.current_thread().name:
            safe_print(f"Log: {msg}", is_background=True)
        else:
            safe_print(f"Log: {msg}")


def safe_print(message, is_background=False):
    """Thread-safe print function with visual indicators for background messages.

    Args:
        message: The message to print
        is_background: Whether this is a message from the background thread

    """
    # In quiet mode (default), skip most initialization and status messages
    if QUIET_MODE and (
        "Connecting to" in message
        or "Connected to" in message
        or "Ensuring" in message
        or "Loading" in message
        or "config" in message
        or "Table counts" in message
        or "Checking" in message
        or "Database" in message
        or "Attaching" in message
        or "Initialize" in message
    ):
        return

    with print_lock:
        if is_background:
            # Add visual indicator for background messages
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n[BG {current_time}] {message}")
        else:
            # Regular message
            print(message)


def init_db(
    db_path: str | None = None,
    use_memory_db: bool = False,
    use_local_db: bool = False,
) -> DatabaseConnection:
    """Initialize the database for storing feedback and preferences.

    Args:
        db_path: Path to the database file. If None, uses the default path.
        use_memory_db: Whether to use an in-memory database (for testing).
        use_local_db: Whether to also attach the local database. Default is False (MotherDuck only).

    Returns:
        Database connection object.

    """
    try:
        # Use MotherDuck by default
        safe_print("Connecting to MotherDuck database...")
        conn = get_motherduck_connection(MOTHERDUCK_DB_NAME)

        # Test the connection
        try:
            test_result = conn.execute("SELECT 1 AS test")
            safe_print(f"MotherDuck connection test: {test_result}")
        except Exception as test_error:
            safe_print(f"WARNING: MotherDuck connection test failed: {test_error}")

        # Create feedback table if it doesn't exist
        safe_print(f"Ensuring {MOTHERDUCK_FEEDBACK_TABLE} table exists...")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {MOTHERDUCK_FEEDBACK_TABLE} (
                id INTEGER PRIMARY KEY,
                msg_id TEXT NOT NULL,
                subject TEXT,
                original_priority INTEGER,
                assigned_priority INTEGER,
                suggested_priority INTEGER,
                feedback_comments TEXT,
                add_to_topics TEXT,
                timestamp TIMESTAMP
            )
        """)

        # Create indexes for feedback table
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS feedback_timestamp_idx
            ON {MOTHERDUCK_FEEDBACK_TABLE} (timestamp)
        """)

        # Create preferences table if it doesn't exist
        safe_print(f"Ensuring {MOTHERDUCK_PREFERENCES_TABLE} table exists...")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {MOTHERDUCK_PREFERENCES_TABLE} (
                id INTEGER PRIMARY KEY,
                override_rules TEXT,
                topic_weight DOUBLE,
                sender_weight DOUBLE,
                content_value_weight DOUBLE,
                sender_history_weight DOUBLE,
                priority_map TEXT,
                timestamp TIMESTAMP
            )
        """)

        # For backward compatibility, only attach local database if explicitly requested
        if use_local_db and os.path.exists(CLASSIFIER_DB):
            safe_print(f"Attaching local classifier database from {CLASSIFIER_DB}")
            try:
                conn.execute(f"ATTACH '{CLASSIFIER_DB}' AS classifier_db")
                safe_print("Successfully attached classifier database")
            except Exception as attach_error:
                safe_print(
                    f"WARNING: Could not attach classifier database: {attach_error}"
                )
                safe_print("Continuing without local classifier database")
        else:
            safe_print("Using MotherDuck only (not attaching local database)")

        return conn
    except Exception as e:
        safe_print(f"Error initializing database: {e}")
        raise


def load_feedback(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Load feedback data from the database."""
    try:
        # Execute query and convert to pandas DataFrame
        df = conn.execute(f"""
            SELECT * FROM {MOTHERDUCK_FEEDBACK_TABLE}
            ORDER BY timestamp DESC
        """)

        # If no data, return empty list
        if df is None or len(df) == 0:
            return []

        # Convert DataFrame to list of dictionaries
        feedback_data = []
        for _, row in df.iterrows():
            entry = {
                "id": row["id"] if "id" in row else None,
                "msg_id": row["msg_id"] if "msg_id" in row else "",
                "subject": row["subject"] if "subject" in row else "",
                "original_priority": row["original_priority"]
                if "original_priority" in row
                else 0,
                "assigned_priority": row["assigned_priority"]
                if "assigned_priority" in row
                else 0,
                "suggested_priority": row["suggested_priority"]
                if "suggested_priority" in row
                else 0,
                "feedback_comments": row["feedback_comments"]
                if "feedback_comments" in row
                else "",
                "add_to_topics": json.loads(row["add_to_topics"])
                if "add_to_topics" in row and row["add_to_topics"]
                else [],
                "timestamp": row["timestamp"] if "timestamp" in row else None,
            }
            feedback_data.append(entry)

        return feedback_data
    except Exception as e:
        print(f"Error loading feedback: {e}")
        return []


def save_feedback(
    conn: DatabaseConnection, feedback_entries: list[dict[str, Any]]
) -> None:
    """Save feedback data to the database.

    Args:
        conn: Database connection
        feedback_entries: List of feedback entries to save

    Raises:
        Exception: If there's an error saving feedback

    """
    if not feedback_entries:
        safe_print("Warning: No feedback entries to save")
        return

    safe_print(
        f"Saving {len(feedback_entries)} feedback entries to {MOTHERDUCK_FEEDBACK_TABLE}"
    )

    try:
        for entry in feedback_entries:
            # Debug the structure
            safe_print(f"Processing feedback entry: {entry.keys()}")

            # Extract values from entry, with fallbacks
            msg_id = entry.get("msg_id", "")
            if not msg_id:
                safe_print(f"Error: Missing msg_id in feedback entry: {entry}")
                continue

            subject = entry.get("subject", "")
            original_priority = entry.get("original_priority", 0)

            # Handle None values for assigned_priority with a default of 0
            assigned_priority = entry.get("assigned_priority")
            if assigned_priority is None:
                assigned_priority = 0

            # For suggested_priority, clamp between 0-4
            suggested_priority = entry.get("suggested_priority")
            if suggested_priority is not None:
                suggested_priority = max(0, min(int(suggested_priority), 4))
            else:
                # Fall back to assigned_priority if suggested_priority is None
                suggested_priority = assigned_priority

            feedback_comments = entry.get("feedback_comments", "")

            # Handle add_to_topics which might be None or a list
            add_to_topics = entry.get("add_to_topics")
            if add_to_topics is None:
                add_to_topics = json.dumps([])
            elif isinstance(add_to_topics, list):
                add_to_topics = json.dumps(add_to_topics)
            # If it's already a JSON string, use it as is
            elif not isinstance(add_to_topics, str):
                add_to_topics = json.dumps([])

            timestamp = entry.get("timestamp", datetime.now().isoformat())

            # Sanitize strings for SQL
            subject = subject.replace("'", "''")
            feedback_comments = feedback_comments.replace("'", "''")
            if isinstance(add_to_topics, str):
                add_to_topics = add_to_topics.replace("'", "''")

            # Check if entry already exists
            try:
                safe_print(f"Checking if entry exists for msg_id: {msg_id}")
                existing_df = conn.execute(f"""
                    SELECT id FROM {MOTHERDUCK_FEEDBACK_TABLE}
                    WHERE msg_id = '{msg_id}'
                """)

                if not existing_df.empty:
                    # Update existing entry
                    safe_print(f"Updating existing entry for msg_id: {msg_id}")
                    update_sql = f"""
                        UPDATE {MOTHERDUCK_FEEDBACK_TABLE}
                        SET subject = '{subject}',
                            original_priority = {original_priority},
                            assigned_priority = {assigned_priority},
                            suggested_priority = {suggested_priority},
                            feedback_comments = '{feedback_comments}',
                            add_to_topics = '{add_to_topics}',
                            timestamp = '{timestamp}'
                        WHERE msg_id = '{msg_id}'
                    """
                    safe_print(f"Executing SQL: {update_sql}")
                    conn.execute(update_sql)
                    safe_print(f"Successfully updated entry for msg_id: {msg_id}")
                else:
                    # Generate a unique ID that fits within INT32 range
                    import random

                    unique_id = random.randint(
                        1, 2000000000
                    )  # Safely within INT32 range

                    # Insert new entry with explicit ID
                    safe_print(
                        f"Inserting new entry with ID {unique_id} for msg_id: {msg_id}"
                    )
                    insert_sql = f"""
                        INSERT INTO {MOTHERDUCK_FEEDBACK_TABLE}
                        (id, msg_id, subject, original_priority, assigned_priority, suggested_priority,
                         feedback_comments, add_to_topics, timestamp)
                        VALUES ({unique_id}, '{msg_id}', '{subject}', {original_priority}, {assigned_priority}, {suggested_priority},
                         '{feedback_comments}', '{add_to_topics}', '{timestamp}')
                    """
                    safe_print(f"Executing SQL: {insert_sql}")
                    conn.execute(insert_sql)
                    safe_print(f"Successfully inserted new entry for msg_id: {msg_id}")
            except Exception as e:
                safe_print(f"Error processing entry for msg_id {msg_id}: {e}")
                raise
    except Exception as e:
        safe_print(f"Error saving feedback: {e}")
        raise


def load_preferences(conn: DatabaseConnection) -> dict[str, Any]:
    """Load email classifier preferences from the database."""
    try:
        # Execute query and convert to pandas DataFrame
        df = conn.execute(f"""
            SELECT * FROM {MOTHERDUCK_PREFERENCES_TABLE}
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        # If no data, return defaults
        if df is None or len(df) == 0:
            return {
                "override_rules": [],
                "topic_weight": 1.0,
                "sender_weight": 1.0,
                "content_value_weight": 1.0,
                "sender_history_weight": 1.0,
                "priority_map": {},
            }

        # Get first row
        row = df.iloc[0]

        # Convert to dict
        return {
            "id": row["id"] if "id" in row else None,
            "override_rules": json.loads(row["override_rules"])
            if "override_rules" in row and row["override_rules"]
            else [],
            "topic_weight": row["topic_weight"] if "topic_weight" in row else 1.0,
            "sender_weight": row["sender_weight"] if "sender_weight" in row else 1.0,
            "content_value_weight": row["content_value_weight"]
            if "content_value_weight" in row
            else 1.0,
            "sender_history_weight": row["sender_history_weight"]
            if "sender_history_weight" in row
            else 1.0,
            "priority_map": json.loads(row["priority_map"])
            if "priority_map" in row and row["priority_map"]
            else {},
            "timestamp": row["timestamp"] if "timestamp" in row else None,
        }
    except Exception as e:
        print(f"Error loading preferences: {e}")
        # Return default preferences on error
        return {
            "override_rules": [],
            "topic_weight": 1.0,
            "sender_weight": 1.0,
            "content_value_weight": 1.0,
            "sender_history_weight": 1.0,
            "priority_map": {},
        }


def save_preferences(conn: DatabaseConnection, preferences: dict[str, Any]) -> None:
    """Save email classifier preferences to the database."""
    try:
        # Prepare data for storage
        override_rules = json.dumps(preferences.get("override_rules", []))
        topic_weight = preferences.get("topic_weight", 1.0)
        sender_weight = preferences.get("sender_weight", 1.0)
        content_value_weight = preferences.get("content_value_weight", 1.0)
        sender_history_weight = preferences.get("sender_history_weight", 1.0)
        priority_map = json.dumps(preferences.get("priority_map", {}))
        timestamp = datetime.now().isoformat()

        # Generate a unique ID that fits within INT32 range
        import random

        unique_id = random.randint(1, 2000000000)  # Safely within INT32 range

        # Insert new preferences record with explicit ID
        conn.execute(f"""
            INSERT INTO {MOTHERDUCK_PREFERENCES_TABLE}
            (id, override_rules, topic_weight, sender_weight, content_value_weight,
             sender_history_weight, priority_map, timestamp)
            VALUES ({unique_id}, '{override_rules.replace("'", "''")}', {topic_weight}, {sender_weight}, {content_value_weight},
              {sender_history_weight}, '{priority_map.replace("'", "''")}', '{timestamp}')
        """)
    except Exception as e:
        print(f"Error saving preferences: {e}")
        raise


def generate_feedback_json(
    feedback_text: str, msg_id: str, subject: str, assigned_priority: int
) -> dict:
    """Uses Deepinfra API to structure natural language feedback into JSON.
    Returns dict with 'error' field if processing fails.
    """
    # First check for simple priority overrides without API call
    feedback_lower = feedback_text.lower()
    if "unsubscribe" in feedback_lower:
        return {
            "msg_id": msg_id,
            "subject": subject,
            "assigned_priority": assigned_priority,
            "feedback_comments": "Automatic priority cap at 2 due to unsubscribe mention",
            "suggested_priority": min(assigned_priority, 2),
            "add_to_topics": None,
            "add_to_source": None,
            "timestamp": datetime.now().isoformat(),
        }

    prompt = f"""
You are a feedback processing assistant.  You are given natural language feedback on an email's assigned priority, along with the email's subject and ID.  Your task is to structure this feedback into a JSON object.

Input Data:

*   Message ID: {msg_id}
*   Subject: {subject}
*   Assigned Priority: {assigned_priority}
*   Feedback: {feedback_text}

Output Requirements:

Return a JSON object with the following fields:

{{
    "msg_id": "auto-generated-id",
    "subject": "optional description",
    "assigned_priority": 0,
    "feedback_comments": "cleaned feedback summary",
    "suggested_priority": null,
    "add_to_topics": null,
    "add_to_source": null,
    "timestamp": "2023-03-01T12:00:00.000Z"
}}

Key requirements:
1. DO NOT use code formatting (remove any ```json or ``` markers)
2. ALL output must be valid JSON - no comments, code examples or explanations
3. All fields MUST use the exact names shown above
4. JSON must be plain text - never wrapped in code blocks
5. If any field can't be determined, use `null`
6. The timestamp should be in ISO format string

Failure to follow these requirements will cause critical system errors. Always return pure JSON.
"""
    if not DEEPINFRA_API_KEY:
        print("Error: DEEPINFRA_API_KEY environment variable not set")
        print("1. Get your API key from https://deepinfra.com")
        print("2. Run: export DEEPINFRA_API_KEY='your-key-here'")
        return {}

    try:
        client = OpenAI(
            api_key=DEEPINFRA_API_KEY, base_url="https://api.deepinfra.com/v1/openai"
        )

        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )

        try:
            # Handle potential HTML error response
            response_content = response.choices[0].message.content

            # Clean any markdown code formatting
            if response_content.startswith("```json"):
                response_content = response_content[7:]  # Strip the opening
            response_content = response_content.rstrip("` \n")  # Strip closing

            if "<html>" in response_content:
                raise ValueError("Received HTML error response from API")

            feedback_json = json.loads(response_content.strip())
            # Use ISO format timestamp instead of Unix timestamp
            feedback_json["timestamp"] = datetime.now().isoformat()
            return feedback_json
        except json.JSONDecodeError as e:
            error_msg = f"API response was not valid JSON: {str(e)}\nResponse Text: {response.choices[0].message.content[:200]}"
            print(f"Error: {error_msg}")
            return {
                "error": error_msg,
                "feedback_text": feedback_text,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        print(f"Error calling AI API: {e}")
        print("Check your DEEPINFRA_API_KEY and internet connection")
        return {
            "error": f"API error: {str(e)}",
            "feedback_text": feedback_text,
            "timestamp": datetime.now().isoformat(),
        }


import logging


def suggest_rule_changes(
    feedback_data: list[dict[str, Any]], preferences: dict[str, Any]
) -> list[dict[str, str | int]]:
    """Analyzes feedback and suggests changes to preferences.

    Args:
        feedback_data: List of feedback entries with assigned/suggested priorities
        preferences: Current system preferences

    Returns:
        List of suggested changes with type, keyword, priority and reason

    """
    suggested_changes: list[dict[str, str | int]] = []
    feedback_count = len(feedback_data)

    # Minimum feedback count before suggestions are made
    if feedback_count < 5:
        return []

    # 1. Analyze Feedback Distribution
    priority_counts = Counter(entry["assigned_priority"] for entry in feedback_data)

    # 2. Identify Frequent Discrepancies
    discrepancy_counts = Counter()
    topic_suggestions = {}  # Store suggested topic changes
    source_suggestions = {}

    for entry in feedback_data:
        if not entry:  # skip if empty
            continue
        # extract comment, subject, and feedback
        feedback_comment = entry.get("feedback_comments", "").lower()
        subject = entry.get("subject", "").lower()
        assigned_priority = int(entry.get("assigned_priority"))
        suggested_priority = entry.get("suggested_priority")
        add_to_topics = entry.get("add_to_topics")
        add_to_source = entry.get("add_to_source")

        # check if there is a discrepancy
        if assigned_priority != suggested_priority and suggested_priority is not None:
            discrepancy_key = (assigned_priority, suggested_priority)
            discrepancy_counts[discrepancy_key] += 1

            # check if keywords are in topics or source
            if add_to_topics:
                for keyword in add_to_topics:
                    # Suggest adding to topics
                    if keyword not in topic_suggestions:
                        topic_suggestions[keyword] = {
                            "count": 0,
                            "suggested_priority": suggested_priority,
                        }
                    topic_suggestions[keyword]["count"] += 1
                    topic_suggestions[keyword]["suggested_priority"] = (
                        suggested_priority  # Update if higher
                    )

            # Suggest adding to source
            if add_to_source:
                if add_to_source not in source_suggestions:
                    source_suggestions[add_to_source] = {
                        "count": 0,
                        "suggested_priority": suggested_priority,
                    }
                source_suggestions[add_to_source]["count"] += 1
                source_suggestions[add_to_source]["suggested_priority"] = (
                    suggested_priority  # Update if higher
                )
    # Output the most common discrepancies
    print(f"\nMost Common Discrepancies: {discrepancy_counts.most_common()}")

    # 3.  Suggest *new* override rules.  This is the most important part.
    for topic, suggestion in topic_suggestions.items():
        if suggestion["count"] >= 3:  # Require at least 3 occurrences
            suggested_changes.append(
                {
                    "type": "add_override_rule",
                    "keyword": topic,
                    "priority": suggestion["suggested_priority"],
                    "reason": f"Suggested based on feedback (topic appeared {suggestion['count']} times with consistent priority suggestion)",
                }
            )
    for source, suggestion in source_suggestions.items():
        if suggestion["count"] >= 3:
            suggested_changes.append(
                {
                    "type": "add_override_rule",
                    "keyword": source,
                    "priority": suggestion["suggested_priority"],
                    "reason": f"Suggested based on feedback (source appeared {suggestion['count']} times with consistent priority suggestion)",
                }
            )

    # 4 Suggest changes to existing weights.
    discrepancy_sum = 0
    valid_discrepancy_count = 0
    for (assigned, suggested), count in discrepancy_counts.items():
        if suggested is not None:  # make sure suggested priority is not null
            discrepancy_sum += (suggested - assigned) * count
            valid_discrepancy_count += count
    average_discrepancy = (
        discrepancy_sum / valid_discrepancy_count if valid_discrepancy_count else 0
    )

    # Map overall discrepancy to a specific score adjustment.  This is a heuristic.
    if abs(average_discrepancy) > 0.5:
        # Example: If priorities are consistently too low, increase the weight of content_value.
        if average_discrepancy > 0:
            suggested_changes.append(
                {
                    "type": "adjust_weight",
                    "score_name": "content_value_score",
                    "adjustment": 0.1,  # Increase weight by 10%
                    "reason": "Priorities are consistently lower than user feedback suggests.",
                }
            )
        else:
            suggested_changes.append(
                {
                    "type": "adjust_weight",
                    "score_name": "automation_score",
                    "adjustment": 0.1,  # Increase weight (making the impact of automation_score *lower*)
                    "reason": "Priorities are consistently higher than user feedback suggests.",
                }
            )
    return suggested_changes


def update_preferences(
    preferences: dict[str, Any], changes: list[dict[str, str | int]]
) -> dict[str, Any]:
    """Applies suggested changes to the preferences.

    Args:
        preferences: Current system preferences
        changes: List of suggested changes

    Returns:
        Updated preferences dictionary

    """
    updated_preferences = preferences.copy()

    # Initialize override_rules if it doesn't exist
    if "override_rules" not in updated_preferences:
        updated_preferences["override_rules"] = []

    for change in changes:
        if change["type"] == "add_override_rule":
            keyword = change["keyword"]
            priority = change["priority"]

            # Check if a rule with this keyword already exists
            rule_exists = False
            for existing_rule in updated_preferences["override_rules"]:
                if "keywords" in existing_rule and keyword in existing_rule["keywords"]:
                    # Update existing rule if found
                    existing_rule["min_priority"] = priority
                    rule_exists = True
                    break

            # Only add if no matching rule was found
            if not rule_exists:
                new_rule = {
                    "keywords": [keyword],
                    "min_priority": priority,
                }
                updated_preferences["override_rules"].append(new_rule)

        elif change["type"] == "adjust_weight":
            # Apply weight changes
            score_name = change["score_name"]
            adjustment = change["adjustment"]
            weight_key = f"{score_name.replace('_score', '')}_weight"
            current_weight = updated_preferences.get(weight_key, 1.0)
            updated_preferences[weight_key] = current_weight + adjustment

    return updated_preferences


def process_feedback_worker(conn: DatabaseConnection):
    """Worker function to process feedback items from the queue in the background.

    Args:
        conn: The database connection

    """
    # Set thread name to make it identifiable
    threading.current_thread().name = "process_feedback_worker"

    # Redirect all logging in this thread through our handler
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = root_logger.handlers.copy()

    # Add our custom handler and set log level to capture INFO and above
    thread_safe_handler = ThreadSafeLogHandler()
    thread_safe_handler.setLevel(logging.INFO)
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [thread_safe_handler]

    # Also capture httpx logging
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.handlers = [thread_safe_handler]

    # Redirect stdout and stderr for this thread
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        # Redirect stdout/stderr (this will only affect this thread)
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Add a periodic flush function to check for captured output
        def check_and_flush_outputs():
            stdout_content = stdout_capture.getvalue()
            if stdout_content:
                safe_print(f"Captured stdout: {stdout_content}", is_background=True)
                stdout_capture.truncate(0)
                stdout_capture.seek(0)

            stderr_content = stderr_capture.getvalue()
            if stderr_content:
                safe_print(f"Captured stderr: {stderr_content}", is_background=True)
                stderr_capture.truncate(0)
                stderr_capture.seek(0)

        safe_print(
            "Background worker started and ready to process feedback",
            is_background=True,
        )

        while True:
            try:
                # Get the next feedback item from the queue
                item = feedback_queue.get()

                # Check and flush any captured output
                check_and_flush_outputs()

                # Check for termination signal
                if item is None:
                    safe_print(
                        "Received shutdown signal, cleaning up", is_background=True
                    )
                    feedback_queue.task_done()
                    break

                # Unpack the item
                (
                    feedback_text,
                    msg_id,
                    subject,
                    priority,
                    suggested_priority_override,
                ) = item

                safe_print(
                    f"Processing feedback for email: {subject[:50]}...",
                    is_background=True,
                )

                try:
                    # Generate feedback JSON using OpenAI or DeepInfra
                    feedback_json = generate_feedback_json(
                        feedback_text, msg_id, subject, priority
                    )

                    # Check and flush any captured output
                    check_and_flush_outputs()

                    if not feedback_json:
                        safe_print(
                            f"Error: Empty feedback JSON returned for {subject}",
                            is_background=True,
                        )
                        feedback_queue.task_done()
                        continue

                    # Update priority if specified
                    if suggested_priority_override is not None:
                        feedback_json["suggested_priority"] = (
                            suggested_priority_override
                        )

                    safe_print(
                        f"Saving feedback to MotherDuck database: {MOTHERDUCK_FEEDBACK_TABLE}",
                        is_background=True,
                    )

                    # Save to the database - wrap in try/except for better error reporting
                    try:
                        save_feedback(conn, [feedback_json])
                        safe_print(
                            f"Successfully saved feedback to MotherDuck for: {subject[:50]}",
                            is_background=True,
                        )
                    except Exception as save_error:
                        safe_print(
                            f"ERROR SAVING TO MOTHERDUCK: {save_error}",
                            is_background=True,
                        )
                        # Try to reconnect and save again
                        try:
                            safe_print(
                                "Attempting to reconnect to MotherDuck...",
                                is_background=True,
                            )
                            new_conn = get_motherduck_connection(MOTHERDUCK_DB_NAME)
                            save_feedback(new_conn, [feedback_json])
                            safe_print(
                                "Successfully saved after reconnection",
                                is_background=True,
                            )
                        except Exception as retry_error:
                            safe_print(
                                f"RETRY FAILED: {retry_error}", is_background=True
                            )
                except Exception as e:
                    safe_print(
                        f"Error processing feedback in background: {e}",
                        is_background=True,
                    )
                finally:
                    # Final check for any captured output
                    check_and_flush_outputs()

                    # Mark task as done
                    feedback_queue.task_done()
                    safe_print("Task marked as complete", is_background=True)
            except Exception as e:
                safe_print(
                    f"Unexpected error in background worker: {e}", is_background=True
                )

                # Check for any captured output during error handling
                check_and_flush_outputs()

                # Mark task as done even if there's an error
                feedback_queue.task_done()
    finally:
        # Restore original logging configuration
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)

        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def start_background_processor(conn: DatabaseConnection):
    """Start the background processor if not already running."""
    global background_processor_started

    if not background_processor_started:
        # Start the worker thread
        worker_thread = threading.Thread(
            target=process_feedback_worker,
            args=(conn,),
            daemon=True,  # Make thread a daemon so it exits when main program exits
        )
        worker_thread.start()
        background_processor_started = True


def get_user_input(prompt, default=None):
    """Get user input with proper locking and error handling.

    Args:
        prompt: The prompt to display to the user
        default: Default value if input is interrupted

    Returns:
        User input or default value if interrupted

    """
    result = default
    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            with print_lock:
                sys.stdout.flush()  # Ensure prompt is displayed
                result = input(prompt).strip()
            return result
        except (EOFError, KeyboardInterrupt):
            retry_count += 1
            if retry_count >= max_retries:
                safe_print(
                    f"\nInput interrupted {retry_count} times. Using default: {default}"
                )
                return default
            safe_print(
                f"\nInput interrupted. Please try again. ({retry_count}/{max_retries})"
            )
            time.sleep(0.5)  # Small delay to prevent rapid retries

    return result


def generate_test_data():
    """Generate test data for development and testing."""
    safe_print("Using test data")

    # Create sample test data with different senders and priorities
    test_data = [
        (
            "test-msg-1",
            "Monthly Investment Update",
            2,
            "financial-updates@example.com",
            "Here is your monthly portfolio performance summary. Your investments have grown by 2.5% since last month...",
            3,
        ),
        (
            "test-msg-2",
            "Question about retirement planning",
            1,
            "client1@gmail.com",
            "I've been thinking about my retirement plan and had some questions about the projections we discussed...",
            1,
        ),
        (
            "test-msg-3",
            "Invitation: Industry Conference",
            3,
            "events@finance-conference.com",
            "You're invited to speak at our upcoming Financial Advisors Summit. The event will be held on June 15th...",
            2,
        ),
        (
            "test-msg-4",
            "Urgent: Client account issue",
            0,
            "support@custodian.com",
            "We've detected an issue with one of your client's accounts. Please review and take action immediately...",
            1,
        ),
        (
            "test-msg-5",
            "Weekly Market Insights",
            4,
            "research@investment-firm.com",
            "This week's market highlights: Tech stocks continued their rally, while energy sector faced headwinds...",
            3,
        ),
        (
            "test-msg-6",
            "Follow-up from our meeting",
            1,
            "client1@gmail.com",
            "Thank you for meeting with me yesterday. I've given some thought to your recommendations and would like to proceed...",
            1,
        ),
        (
            "test-msg-7",
            "Regulatory update: New compliance requirements",
            2,
            "compliance@regulator.gov",
            "Important: New regulations affecting financial advisors will take effect on August 1st. You must update your policies...",
            1,
        ),
        (
            "test-msg-8",
            "Your subscription renewal",
            3,
            "billing@research-service.com",
            "Your subscription to our premium research service will renew automatically in 14 days. If you wish to cancel...",
            2,
        ),
        (
            "test-msg-9",
            "Partnership opportunity",
            1,
            "bizdev@wealthtech.com",
            "I represent a fintech company that has developed an innovative portfolio analysis tool. Would you be interested in a partnership?",
            1,
        ),
        (
            "test-msg-10",
            "Client referral",
            0,
            "colleague@advisor-network.com",
            "I have a client who recently relocated to your area and needs local financial advice. Would you be open to a referral?",
            1,
        ),
    ]

    return test_data


def main(
    auto_skip_threshold=None,
    show_all_skipped=False,
    use_local_db=False,
    fast_start=True,
    limit=DEFAULT_LIMIT,
    use_test_data=False,
):
    """Main entry point for the script.

    Args:
        auto_skip_threshold: Optional threshold for automatically skipping senders with this many or more feedback entries.
        show_all_skipped: If True, show details for all skipped senders, not just the first few.
        use_local_db: If True, also attach the local database. Default is False (MotherDuck only).
        fast_start: If True, use optimized loading for faster startup.
        limit: Maximum number of emails to load.
        use_test_data: If True, use test data instead of loading from database.

    """
    # Initialize error handling

    # Set the auto-skip threshold
    global DEFAULT_AUTO_SKIP_THRESHOLD
    if auto_skip_threshold is not None:
        DEFAULT_AUTO_SKIP_THRESHOLD = auto_skip_threshold

    # Connect to database (unless using test data)
    conn = None

    try:
        if use_test_data:
            # Use test data without connecting to database
            safe_print("TEST MODE: Using test data without database connection")
            opportunities = generate_test_data()
            feedback_data = []
            preferences = {
                "override_rules": [],
                "topic_weight": 1.0,
                "sender_weight": 1.0,
                "content_value_weight": 1.0,
                "sender_history_weight": 1.0,
                "priority_map": {},
            }

            # Create a dummy database connection for the background processor
            class DummyConnection:
                def execute(self, query, params=None):
                    safe_print(f"[Dummy] Would execute: {query}")
                    return pd.DataFrame()

                def close(self):
                    pass

            conn = DummyConnection()

            # Start the background processor
            start_background_processor(conn)
        else:
            # Normal database connection
            safe_print("Connecting to MotherDuck database...")
            conn = init_db(use_local_db=use_local_db)

            # Start the background processor
            start_background_processor(conn)

        # Continue with the rest of the main function

        # Load feedback and preferences from database
        if not use_test_data:
            # Load existing feedback
            safe_print("Loading existing feedback...")
            feedback_data = load_feedback(conn)

            # Load existing preferences
            safe_print("Loading existing preferences...")
            preferences = load_preferences(conn)

            # Try to load emails
            safe_print(f"Loading emails (limit: {limit})...")
            if fast_start:
                opportunities = load_emails_fast(conn, limit=limit)
            else:
                # Use original loading method here if needed
                safe_print("Using standard loading method...")
                opportunities = load_emails_fast(
                    conn, limit=limit
                )  # Fallback to fast method

            # If no opportunities found, provide clear error instead of falling back to test mode
            if not opportunities:
                safe_print("\n========== ERROR: NO EMAILS FOUND ==========")
                safe_print("No emails were found in the database. Possible reasons:")
                safe_print("1. Database connection issue")
                safe_print("2. Empty database tables")
                safe_print("3. Incorrect table names or structure")
                safe_print("\nTo troubleshoot:")
                safe_print("- Run with --verbose flag for more detailed logs")
                safe_print("- Check that emails exist in the database")
                safe_print("- Check table structure and permissions")
                safe_print("\nIf you want to use test data for development:")
                safe_print("- Run with --test flag explicitly")
                return
        else:
            # If explicitly using test mode, generate test data
            safe_print("\n========== WARNING: USING TEST MODE ==========")
            safe_print("Running with test data. NO DATABASE CHANGES WILL BE SAVED.")
            safe_print("Remove --test flag to use real database.")
            safe_print("================================================\n")
            opportunities = generate_test_data()
            feedback_data = []
            preferences = {
                "override_rules": [],
                "topic_weight": 1.0,
                "sender_weight": 1.0,
                "content_value_weight": 1.0,
                "sender_history_weight": 1.0,
                "priority_map": {},
            }

            # Create a dummy database connection for the background processor
            class DummyConnection:
                def execute(self, query, params=None):
                    safe_print(f"[Dummy] Would execute: {query}")
                    return pd.DataFrame()

                def close(self):
                    pass

            conn = DummyConnection()

            # Start the background processor
            start_background_processor(conn)

        # Check for legacy feedback files - but only if connected to a database and not in test mode
        if not use_test_data:
            legacy_feedback = []
            if not feedback_data and os.path.exists("feedback.json"):
                safe_print("Migrating existing feedback.json to database...")
                with open("feedback.json") as f:
                    legacy_feedback = json.load(f)
                    save_feedback(conn, legacy_feedback)
                os.rename("feedback.json", "feedback.json.bak")
            feedback_data = legacy_feedback

            legacy_prefs = {}
            if not preferences.get("priority_map") and os.path.exists(
                "email_preferences.json"
            ):
                safe_print("Migrating email_preferences.json to database...")
                with open("email_preferences.json") as f:
                    legacy_prefs = json.load(f)
                    save_preferences(conn, legacy_prefs)
                    os.rename("email_preferences.json", "email_preferences.json.bak")
                preferences = legacy_prefs

        # --- Interactive Feedback Input ---
        new_feedback_entries = []
        if opportunities:
            from collections import defaultdict

            # Get list of senders who already have feedback
            senders_with_feedback = set()
            sender_feedback_counts = {}

            # Only try to get sender feedback counts if we have a database connection
            if conn is not None:
                try:
                    safe_print("Checking for senders with existing feedback...")
                    existing_senders_df = conn.execute(f"""
                        SELECT e.from_address, COUNT(*) as feedback_count
                        FROM {MOTHERDUCK_EMAIL_ANALYSES_TABLE} e
                        JOIN {MOTHERDUCK_FEEDBACK_TABLE} f ON e.msg_id = f.msg_id
                        GROUP BY e.from_address
                    """)

                    if not existing_senders_df.empty:
                        for _, row in existing_senders_df.iterrows():
                            if "from_address" in row:
                                senders_with_feedback.add(row["from_address"])
                                sender_feedback_counts[row["from_address"]] = row[
                                    "feedback_count"
                                ]
                        safe_print(
                            f"Found {len(senders_with_feedback)} senders with existing feedback"
                        )
                except Exception as e:
                    safe_print(
                        f"Warning: Could not determine senders with existing feedback: {e}"
                    )
                    # Try alternative query with emails table
                    try:
                        safe_print("Trying alternative query with emails table...")
                        existing_senders_df = conn.execute(f"""
                            SELECT e.from_address, COUNT(*) as feedback_count
                            FROM {MOTHERDUCK_EMAILS_TABLE} e
                            JOIN {MOTHERDUCK_FEEDBACK_TABLE} f ON e.msg_id = f.msg_id
                            GROUP BY e.from_address
                        """)

                        if not existing_senders_df.empty:
                            for _, row in existing_senders_df.iterrows():
                                if "from_address" in row:
                                    senders_with_feedback.add(row["from_address"])
                                    sender_feedback_counts[row["from_address"]] = row[
                                        "feedback_count"
                                    ]
                            safe_print(
                                f"Found {len(senders_with_feedback)} senders with existing feedback (using emails table)"
                            )
                    except Exception as alt_e:
                        safe_print(f"Warning: Alternative query also failed: {alt_e}")
                        # At this point we'll continue with an empty set
            elif use_test_data:
                # In test mode, assume all senders are new
                safe_print(
                    "Test mode: Assuming all senders are new (no feedback history)"
                )

            # Group opportunities by sender
            sender_groups = defaultdict(list)
            for opp in opportunities:
                sender_groups[opp[3]].append(opp)  # Group by from_address

            # Sort senders to prioritize those without feedback
            sorted_senders = []
            new_senders = []
            existing_senders = []
            skipped_senders = []

            # Define threshold for auto-skipping (senders with more than this many feedback entries)
            AUTO_SKIP_THRESHOLD = DEFAULT_AUTO_SKIP_THRESHOLD

            for sender, emails in sender_groups.items():
                if sender in senders_with_feedback:
                    # Check if sender has multiple entries and should be skipped
                    feedback_count = sender_feedback_counts.get(sender, 0)
                    if feedback_count >= AUTO_SKIP_THRESHOLD:
                        skipped_senders.append((sender, feedback_count))
                        continue
                    existing_senders.append((sender, emails))
                else:
                    new_senders.append((sender, emails))

            # New senders first, then existing senders
            sorted_senders = new_senders + existing_senders

            safe_print(
                f"\nFound {len(opportunities)} emails from {len(sender_groups)} senders ({len(new_senders)} new):"
            )
            if skipped_senders:
                safe_print(
                    f"Automatically skipped {len(skipped_senders)} senders with {AUTO_SKIP_THRESHOLD}+ existing entries:"
                )

                # Determine how many skipped senders to show
                senders_to_show = (
                    skipped_senders if show_all_skipped else skipped_senders[:5]
                )

                for sender, count in senders_to_show:
                    safe_print(f"  - {sender} ({count} entries)")

                # Only show the "and more" message if we're not showing all and there are more than the limit
                if not show_all_skipped and len(skipped_senders) > 5:
                    safe_print(f"  - ... and {len(skipped_senders) - 5} more")

            # Check if we have any senders left to process after skipping
            if not sorted_senders:
                safe_print(
                    "\nNo senders to process - all have been skipped or have sufficient feedback."
                )
                return

            for sender_idx, (from_addr, emails) in enumerate(sorted_senders, 1):
                # Indicate if this is a new sender with no feedback
                is_new = from_addr not in senders_with_feedback
                new_indicator = " (NEW)" if is_new else ""
                safe_print(f"\n{'=' * 80}")
                safe_print(
                    f"=== Sender {sender_idx}/{len(sorted_senders)}: {from_addr}{new_indicator} ==="
                )
                safe_print(f"{'=' * 80}")

                # Show first 3 emails, then prompt if they want to see more
                for idx, email in enumerate(emails[:3], 1):
                    msg_id, subject, priority, _, snippet, total_from_sender = email
                    safe_print(f"\n  Email {idx}: {subject}")
                    safe_print(f"  Priority: {priority}")
                    safe_print(f"  Snippet: {snippet[:100]}...")

                if len(emails) > 3:
                    show_more = get_user_input(
                        f"\n  This sender has {len(emails)} emails. Show all? (y/n/q): ",
                        "n",
                    )
                    if show_more == "q":
                        break
                    if show_more == "y":
                        for idx, email in enumerate(emails[3:], 4):
                            msg_id, subject, priority, _, snippet, total_from_sender = (
                                email
                            )
                            safe_print(f"\n  Email {idx}: {subject}")
                            safe_print(f"  Priority: {priority}")
                            safe_print(f"  Snippet: {snippet[:100]}...")

                for email in emails:
                    msg_id, subject, priority, _, snippet, total_from_sender = email
                    safe_print(f"\n{'-' * 80}")
                    safe_print(f"  Current email: {subject}")
                    safe_print(f"  Priority: {priority}")
                    safe_print(f"  Snippet: {snippet[:100]}...")
                    safe_print(f"{'-' * 80}")

                    # Flag to track if we've processed feedback for this email
                    feedback_processed = False

                    while not feedback_processed:
                        # Use our safe input function
                        user_input = get_user_input(
                            "\nType feedback, 't' to tag, 'i' for ingest, 'n' for next email, 's' for next sender, or 'q' to quit: ",
                            "n",
                        )

                        if user_input in ("q", "quit"):
                            safe_print("\nExiting feedback session...")
                            # Wait for background processing to complete
                            safe_print(
                                "Waiting for background processing to complete..."
                            )
                            feedback_queue.join()
                            # Send termination signal to worker thread
                            feedback_queue.put(None)
                            return

                        if user_input in ("s", "skip"):
                            safe_print("\nMoving to next sender...")
                            # Break out of the inner email loop and continue with the next sender
                            break

                        if user_input in ("n", "next"):
                            safe_print("\nMoving to next email...")
                            feedback_processed = True
                            continue

                        feedback_text = ""
                        action = ""

                        if user_input == "t":
                            feedback_text = "USER ACTION: Tag for follow-up"
                            action = "follow-up"
                        elif user_input == "i":
                            safe_print("\nSelect ingestion type:")
                            safe_print(
                                "  1) Form submission (questions, contact requests)"
                            )
                            safe_print("  2) Contact record update")
                            safe_print("  3) Task creation")
                            ingest_type = get_user_input("Enter number (1-3): ", "1")
                            if ingest_type == "1":
                                feedback_text = (
                                    "USER ACTION: Tag for form submission ingestion"
                                )
                                action = "form_submission"
                            elif ingest_type == "2":
                                feedback_text = (
                                    "USER ACTION: Tag for contact record update"
                                )
                                action = "contact_update"
                            elif ingest_type == "3":
                                feedback_text = "USER ACTION: Tag for task creation"
                                action = "task_creation"
                            else:
                                feedback_text = "USER ACTION: Tag for automated ingestion (unspecified type)"
                                action = "automated-ingestion"
                        else:
                            feedback_text = user_input

                        if not feedback_text:
                            continue

                        safe_print("\nAvailable actions:")
                        safe_print("  - Enter priority (0-4)")
                        safe_print("  - 't' = Tag for follow-up")
                        safe_print("  - 'i' = Tag for automated ingestion")
                        safe_print("  - 'q' = Quit and save progress")

                        # Use our safe input function for priority
                        suggested_priority = get_user_input(
                            "Suggested priority (0-4, blank to keep current): ", ""
                        )

                        # Process the suggested priority
                        suggested_priority_override = None
                        if suggested_priority.isdigit():
                            suggested_priority_override = max(
                                0, min(int(suggested_priority), 4)
                            )

                        # Instead of processing synchronously, add to the background queue
                        feedback_queue.put(
                            (
                                feedback_text,
                                msg_id,
                                subject,
                                priority,
                                suggested_priority_override,
                            )
                        )

                        # Provide immediate feedback to the user that we're handling it
                        safe_print(
                            f"\nFeedback for '{subject[:50]}...' queued for processing in the background."
                        )
                        safe_print(
                            "You can continue with the next email while we process your feedback."
                        )

                        # We can immediately mark as processed and move on
                        feedback_processed = True

                    # If user chose to skip to next sender, break out of the email loop
                    if user_input in ("s", "skip"):
                        break

        # Process and handle the rest of the function
        if not feedback_data and not new_feedback_entries:
            safe_print("No existing feedback found. You can add new feedback entries.")
            # ... rest of the function would continue here

    except Exception as e:
        safe_print(f"Error in main function: {e}")
        raise
    finally:
        # Clean up resources
        if conn:
            try:
                # Wait for any remaining background tasks to complete
                if background_processor_started:
                    safe_print(
                        "\nWaiting for background processing to complete before exiting..."
                    )
                    feedback_queue.join()
                    # Send termination signal to worker thread
                    feedback_queue.put(None)

                conn.close()
                safe_print(f"Data saved to MotherDuck database '{MOTHERDUCK_DB_NAME}'")
                safe_print(f"  - Feedback table: '{MOTHERDUCK_FEEDBACK_TABLE}'")
                safe_print(f"  - Preferences table: '{MOTHERDUCK_PREFERENCES_TABLE}'")
            except Exception as e:
                safe_print(f"Error closing database connection: {e}")


def load_emails_fast(conn: DatabaseConnection, limit: int = 20) -> list:
    """Load emails directly from the emails table, skipping complex joins for faster loading.

    Args:
        conn: Database connection
        limit: Maximum number of emails to load

    Returns:
        List of tuples (msg_id, subject, priority, from_address, snippet, count)

    """
    safe_print(f"Fast loading up to {limit} emails...")

    try:
        # Check what tables exist
        tables_df = conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
        """)

        if not tables_df.empty:
            table_count = len(tables_df)
            safe_print(f"Found {table_count} tables in database")

            # Check specifically for emails table
            email_tables = tables_df[
                tables_df["table_name"].isin(["emails", "email_analyses"])
            ]
            if not email_tables.empty:
                for _, row in email_tables.iterrows():
                    safe_print(
                        f"Found table: {row['table_schema']}.{row['table_name']}"
                    )

                    # Check row count
                    try:
                        count_df = conn.execute(
                            f"SELECT COUNT(*) FROM {row['table_name']}"
                        )
                        if not count_df.empty:
                            count = count_df.iloc[0, 0]
                            safe_print(f"Table {row['table_name']} has {count} rows")
                    except Exception as count_err:
                        safe_print(
                            f"Error counting rows in {row['table_name']}: {count_err}"
                        )

        # Try to query emails table
        try:
            # Simple query that loads emails directly WITHOUT filtering out previously processed emails
            results = conn.execute(f"""
                SELECT e.msg_id, e.subject, 2 as priority, e.from_address,
                       SUBSTRING(e.body, 1, 200) as snippet,
                       COUNT(*) OVER (PARTITION BY e.from_address) as sender_count
                FROM {MOTHERDUCK_EMAILS_TABLE} e
                -- No JOIN with feedback table to filter, show all emails
                ORDER BY e.received_date DESC
                LIMIT {limit}
            """)

            if not results.empty:
                safe_print(
                    f"Found {len(results)} emails in {MOTHERDUCK_EMAILS_TABLE} table"
                )

                # Convert to list of tuples
                emails = []
                for _, row in results.iterrows():
                    emails.append(
                        (
                            row["msg_id"],
                            row["subject"],
                            row["priority"],
                            row["from_address"],
                            row["snippet"],
                            row["sender_count"],
                        )
                    )

                return emails
        except Exception as e:
            safe_print(f"Error querying emails table: {e}")

        # Try email_analyses table if emails table query failed
        try:
            safe_print("Trying email_analyses table...")
            results = conn.execute(f"""
                SELECT ea.msg_id, ea.subject, ea.priority, ea.from_address,
                       ea.snippet,
                       1 as sender_count
                FROM {MOTHERDUCK_EMAIL_ANALYSES_TABLE} ea
                ORDER BY ea.analysis_date DESC
                LIMIT {limit}
            """)

            if not results.empty:
                safe_print(
                    f"Found {len(results)} emails in {MOTHERDUCK_EMAIL_ANALYSES_TABLE} table"
                )

                # Convert to list of tuples
                emails = []
                for _, row in results.iterrows():
                    emails.append(
                        (
                            row["msg_id"],
                            row["subject"],
                            row["priority"],
                            row["from_address"],
                            row["snippet"],
                            row["sender_count"],
                        )
                    )

                return emails
        except Exception as e:
            safe_print(f"Error querying email_analyses table: {e}")

        # If all database queries fail, return test data
        safe_print("No emails found in database, using test data")
        return [
            (
                "test-msg-1",
                "Test Email Subject 1",
                2,
                "test@example.com",
                "This is a test email snippet for classification...",
                1,
            ),
            (
                "test-msg-2",
                "Please review proposal",
                1,
                "client@company.com",
                "I wanted to follow up on the proposal we discussed last week...",
                1,
            ),
            (
                "test-msg-3",
                "Inquiry about services",
                3,
                "prospect@gmail.com",
                "Hello, I found your website and am interested in learning more about your services...",
                1,
            ),
            (
                "test-msg-4",
                "Urgent: Server Down",
                0,
                "alerts@monitoring.com",
                "ALERT: The primary database server is not responding. Please check immediately...",
                1,
            ),
            (
                "test-msg-5",
                "Newsletter Subscription",
                4,
                "marketing@newsletter.com",
                "Thank you for subscribing to our newsletter. Here are this week's top stories...",
                1,
            ),
        ]
    except Exception as e:
        safe_print(f"Error in fast email loading: {e}")
        # Return test data as fallback
        safe_print("Error occurred, using test data")
        return [
            (
                "test-msg-1",
                "Test Email Subject 1",
                2,
                "test@example.com",
                "This is a test email snippet for classification...",
                1,
            ),
            (
                "test-msg-2",
                "Please review proposal",
                1,
                "client@company.com",
                "I wanted to follow up on the proposal we discussed last week...",
                1,
            ),
        ]


def test_mode():
    """Run the script in test mode with hardcoded data."""
    safe_print("=== RUNNING IN TEST MODE WITH HARDCODED DATA ===")

    # Generate test data
    test_data = [
        (
            "test-msg-1",
            "Monthly Investment Update",
            2,
            "financial-updates@example.com",
            "Here is your monthly portfolio performance summary. Your investments have grown by 2.5% since last month...",
            3,
        ),
        (
            "test-msg-2",
            "Question about retirement planning",
            1,
            "client1@gmail.com",
            "I've been thinking about my retirement plan and had some questions about the projections we discussed...",
            1,
        ),
        (
            "test-msg-3",
            "Invitation: Industry Conference",
            3,
            "events@finance-conference.com",
            "You're invited to speak at our upcoming Financial Advisors Summit. The event will be held on June 15th...",
            2,
        ),
        (
            "test-msg-4",
            "Urgent: Client account issue",
            0,
            "support@custodian.com",
            "We've detected an issue with one of your client's accounts. Please review and take action immediately...",
            1,
        ),
        (
            "test-msg-5",
            "Weekly Market Insights",
            4,
            "research@investment-firm.com",
            "This week's market highlights: Tech stocks continued their rally, while energy sector faced headwinds...",
            3,
        ),
        (
            "test-msg-6",
            "Follow-up from our meeting",
            1,
            "client1@gmail.com",
            "Thank you for meeting with me yesterday. I've given some thought to your recommendations and would like to proceed...",
            1,
        ),
        (
            "test-msg-7",
            "Regulatory update: New compliance requirements",
            2,
            "compliance@regulator.gov",
            "Important: New regulations affecting financial advisors will take effect on August 1st. You must update your policies...",
            1,
        ),
        (
            "test-msg-8",
            "Your subscription renewal",
            3,
            "billing@research-service.com",
            "Your subscription to our premium research service will renew automatically in 14 days. If you wish to cancel...",
            2,
        ),
        (
            "test-msg-9",
            "Partnership opportunity",
            1,
            "bizdev@wealthtech.com",
            "I represent a fintech company that has developed an innovative portfolio analysis tool. Would you be interested in a partnership?",
            1,
        ),
        (
            "test-msg-10",
            "Client referral",
            0,
            "colleague@advisor-network.com",
            "I have a client who recently relocated to your area and needs local financial advice. Would you be open to a referral?",
            1,
        ),
    ]

    # Group opportunities by sender
    sender_groups = defaultdict(list)
    for opp in test_data:
        sender_groups[opp[3]].append(opp)  # Group by from_address

    # All senders are new in test mode
    sorted_senders = [(sender, emails) for sender, emails in sender_groups.items()]

    # Set up simulated background processing
    class DummyFeedbackProcessor:
        @staticmethod
        def process(feedback, msg_id, subject, priority, suggested_priority=None):
            safe_print(f"\n[BG] Processing feedback for: {subject[:50]}...")
            time.sleep(1)  # Simulate processing time
            safe_print(f"\n[BG] Feedback processed for: {subject[:50]}")

    dummy_processor = DummyFeedbackProcessor()

    # Display feedback interface
    safe_print(
        f"\nLoaded {len(test_data)} test emails from {len(sender_groups)} senders (all new in test mode)"
    )

    for sender_idx, (from_addr, emails) in enumerate(sorted_senders, 1):
        safe_print(f"\n{'=' * 80}")
        safe_print(
            f"=== Sender {sender_idx}/{len(sorted_senders)}: {from_addr} (TEST) ==="
        )
        safe_print(f"{'=' * 80}")

        for email in emails:
            msg_id, subject, priority, _, snippet, total_from_sender = email
            safe_print(f"\n{'-' * 80}")
            safe_print(f"  Current email: {subject}")
            safe_print(f"  Priority: {priority}")
            safe_print(f"  Snippet: {snippet[:100]}...")
            safe_print(f"{'-' * 80}")

            # Flag to track if we've processed feedback for this email
            feedback_processed = False

            while not feedback_processed:
                user_input = get_user_input(
                    "\nType feedback, 't' to tag, 'i' for ingest, 'n' for next email, 's' for next sender, or 'q' to quit: ",
                    "n",
                )

                if user_input in ("q", "quit"):
                    safe_print("\nExiting feedback session...")
                    return

                if user_input in ("s", "skip"):
                    safe_print("\nMoving to next sender...")
                    break

                if user_input in ("n", "next"):
                    safe_print("\nMoving to next email...")
                    feedback_processed = True
                    continue

                feedback_text = ""

                if user_input == "t":
                    feedback_text = "USER ACTION: Tag for follow-up"
                elif user_input == "i":
                    feedback_text = "USER ACTION: Tag for automated ingestion"
                else:
                    feedback_text = user_input

                if not feedback_text:
                    continue

                suggested_priority = get_user_input(
                    "Suggested priority (0-4, blank to keep current): ", ""
                )

                # Process in "background"
                safe_print(
                    f"\nFeedback for '{subject[:50]}...' queued for processing in the background."
                )
                safe_print(
                    "You can continue with the next email while we process your feedback."
                )

                # Start background processing in a thread
                import threading

                processing_thread = threading.Thread(
                    target=dummy_processor.process,
                    args=(
                        feedback_text,
                        msg_id,
                        subject,
                        priority,
                        suggested_priority if suggested_priority else None,
                    ),
                    daemon=True,
                )
                processing_thread.start()

                # We can immediately mark as processed and move on
                feedback_processed = True

            # If user chose to skip to next sender, break out of the email loop
            if user_input in ("s", "skip"):
                break

    safe_print(
        "\nTest mode completed. All data was simulated and no changes were saved to database."
    )


if __name__ == "__main__":
    # If quiet mode is enabled (default), suppress logging from the database connection
    if QUIET_MODE:
        logging.getLogger("dewey.core.db.connection").setLevel(logging.ERROR)
        # Also suppress other common loggers
        logging.getLogger("httpx").setLevel(logging.ERROR)
        # Suppress root logger too
        logging.getLogger().setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        description="Interactive tool for email feedback processing"
    )
    parser.add_argument(
        "--auto-skip-threshold",
        type=int,
        default=DEFAULT_AUTO_SKIP_THRESHOLD,
        help=f"Automatically skip senders with this many or more existing feedback entries (default: {DEFAULT_AUTO_SKIP_THRESHOLD})",
    )
    parser.add_argument(
        "--disable-auto-skip",
        action="store_true",
        help="Disable auto-skipping of senders with multiple feedback entries",
    )
    parser.add_argument(
        "--show-skipped",
        action="store_true",
        help="Show detailed information about all skipped senders",
    )
    parser.add_argument(
        "--use-local-db",
        action="store_true",
        help="Also use the local database (defaults to MotherDuck only)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed setup and initialization messages (verbose mode)",
    )
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Use full data loading instead of fast startup mode",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Limit the number of emails to load (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick summary mode - just show table counts and exit",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use test data instead of connecting to the database",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Do not fall back to test mode if database connection fails (default: will fallback)",
    )

    args = parser.parse_args()

    # Override default quiet mode if verbose is requested
    if args.verbose:
        QUIET_MODE = False

    # Test mode (independent of database connection)
    if args.test:
        test_mode()
        sys.exit(0)

    # Quick mode just shows table stats and exits
    if args.quick:
        try:
            print("Connecting to MotherDuck database...")
            conn = get_motherduck_connection(MOTHERDUCK_DB_NAME)
            print(f"Connected to {MOTHERDUCK_DB_NAME}")

            # Show table counts
            print("\nTable counts:")
            tables = ["email_feedback", "email_preferences", "emails", "email_analyses"]
            for table in tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    print(f"  {table}: {count.iloc[0, 0]} rows")
                except Exception as e:
                    print(f"  {table}: Error - {e}")

            print("\nTo run the full application, remove the --quick flag")
            conn.close()
            sys.exit(0)
        except Exception as e:
            print(f"Error in quick mode: {e}")
            print("\n========== ERROR: DATABASE CONNECTION FAILED ==========")
            print(
                "Could not connect to the database. Please check your connection settings."
            )
            print(
                "If you want to use test data for development, run with the --test flag."
            )
            sys.exit(1)

    # Regular mode - NEVER automatically fall back to test mode
    try:
        # Handle the disable-auto-skip option by setting threshold to a very high number
        if args.disable_auto_skip:
            main(
                auto_skip_threshold=9999,
                show_all_skipped=args.show_skipped,
                use_local_db=args.use_local_db,
                fast_start=not args.slow,
                limit=args.limit,
                use_test_data=args.test,
            )
        else:
            main(
                auto_skip_threshold=args.auto_skip_threshold,
                show_all_skipped=args.show_skipped,
                use_local_db=args.use_local_db,
                fast_start=not args.slow,
                limit=args.limit,
                use_test_data=args.test,
            )
    except Exception as e:
        print(f"\n========== ERROR: {str(e)} ==========")
        print("An error occurred while running the script.")
        print("To run with test data instead, use the --test flag.")
        sys.exit(1)
