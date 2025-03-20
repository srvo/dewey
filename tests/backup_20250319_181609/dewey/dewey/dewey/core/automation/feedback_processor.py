import json
import os
import time
import duckdb
from collections import Counter
from typing import Dict, List
from openai import OpenAI
from dotenv import load_dotenv
import logging
from dewey.core.base_script import BaseScript

ACTIVE_DATA_DIR = "/Users/srvo/input_data/ActiveData"
DB_FILE = f"{ACTIVE_DATA_DIR}/process_feedback.duckdb"
CLASSIFIER_DB = f"{ACTIVE_DATA_DIR}/email_classifier.duckdb"
load_dotenv(os.path.expanduser("~/crm/.env"))
DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")


def init_db(classifier_db_path: str = ""):
    """Initialize database connection and create tables if needed"""
    import time
    max_retries = 5  # Increased from 3
    max_delay = 60  # Max 1 minute between retries
    retry_delay = 2  # seconds (increased initial delay)
    conn = None
    
    # Handle concurrent access with retries
    for attempt in range(max_retries):
        try:
            conn = duckdb.connect(DB_FILE)
            break
        except duckdb.IOException as e:
            if "Conflicting lock" in str(e):
                if attempt < max_retries - 1:
                    print(f"\nDatabase locked by another process (likely your other script)")
                    print(f"Waiting {retry_delay} sec (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_delay)  # Cap max delay
                else:
                    print("\nError: Database still locked after multiple attempts")
                    print("Please close any other processes using the database and try again")
                    sys.exit(1)
            else:
                raise
    
    # Use execute with parameter binding for safety
    with conn:  # Use context manager for transaction
        if classifier_db_path:
            conn.execute(f"ATTACH '{classifier_db_path}' AS classifier_db")
        
        # Create tables using IF NOT EXISTS and proper formatting
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                msg_id VARCHAR PRIMARY KEY,
                subject VARCHAR,
                assigned_priority INTEGER,
                feedback_comments VARCHAR,
                suggested_priority INTEGER,
                add_to_topics VARCHAR[],
                add_to_source VARCHAR,
                timestamp DOUBLE
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key VARCHAR PRIMARY KEY,
                config JSON
            )
        """)
        
        # Add indexes for common queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS feedback_timestamp_idx 
            ON feedback(timestamp)
        """)
    
    # Configure database settings within open connection context
    with conn:
        # Set memory limit and handle transaction
        conn.execute("SET memory_limit='1GB'")
    return conn

def load_feedback(conn) -> List[Dict]:
    """Load feedback entries from database"""
    result = conn.execute("SELECT * FROM feedback").fetchall()
    columns = [col[0] for col in conn.description]
    return [dict(zip(columns, row)) for row in result]

def load_preferences(conn) -> Dict:
    """Load preferences from database"""
    result = conn.execute("SELECT config FROM preferences WHERE key = 'latest'").fetchone()
    return result[0] if result else {"override_rules": []}

def save_feedback(conn, feedback_data: List[Dict]) -> None:
    """Save feedback entries to database"""
    # Upsert feedback entries
    conn.execute("BEGIN TRANSACTION")
    for entry in feedback_data:
        conn.execute("""
            INSERT OR REPLACE INTO feedback 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            entry['msg_id'],
            entry.get('subject'),
            entry.get('assigned_priority'),
            entry.get('feedback_comments'),
            # Clamp priority values between 0-4 and handle invalid types
            max(0, min(int(entry.get('suggested_priority', entry.get('assigned_priority'))), 4)),
            entry.get('add_to_topics'),
            entry.get('add_to_source'),
            entry.get('timestamp')
        ])
    conn.execute("COMMIT")

def save_preferences(conn, preferences: Dict) -> None:
    """Save preferences to database"""
    conn.execute("""
        INSERT OR REPLACE INTO preferences (key, config)
        VALUES ('latest', ?)
    """, [json.dumps(preferences)])

def generate_feedback_json(
    feedback_text: str, msg_id: str, subject: str, assigned_priority: int
) -> Dict:
    """Uses Deepinfra API to structure natural language feedback into JSON.
    Returns dict with 'error' field if processing fails."""

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
            "timestamp": time.time()
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
    "timestamp": 1710300000.123
}}

Key requirements:
1. DO NOT use code formatting (remove any ```json or ``` markers)
2. ALL output must be valid JSON - no comments, code examples or explanations
3. All fields MUST use the exact names shown above
4. JSON must be plain text - never wrapped in code blocks
5. If any field can't be determined, use `null`

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
            feedback_json["timestamp"] = time.time()
            return feedback_json
        except json.JSONDecodeError as e:
            error_msg = f"API response was not valid JSON: {str(e)}\nResponse Text: {response.choices[0].message.content[:200]}"
            print(f"Error: {error_msg}")
            return {"error": error_msg, "feedback_text": feedback_text}
    except Exception as e:
        print(f"Error calling AI API: {e}")
        print(f"Check your DEEPINFRA_API_KEY and internet connection")
        return {}


import time
import logging
from dewey.core.base_script import BaseScript


def suggest_rule_changes(feedback_data: List[Dict], preferences: Dict) -> List[Dict]:
    """Analyzes feedback and suggests changes to preferences."""
    suggested_changes = []
    feedback_count = len(feedback_data)

    # Minimum feedback count before suggestions are made
    if feedback_count < 5:
        print("Not enough feedback data to suggest changes.")
        return []

    # 1. Analyze Feedback Distribution
    priority_counts = Counter(entry["assigned_priority"] for entry in feedback_data)
    print(f"Priority Distribution in Feedback: {priority_counts}")

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
                    topic_suggestions[keyword][
                        "suggested_priority"
                    ] = suggested_priority  # Update if higher

            # Suggest adding to source
            if add_to_source:
                if add_to_source not in source_suggestions:
                    source_suggestions[add_to_source] = {
                        "count": 0,
                        "suggested_priority": suggested_priority,
                    }
                source_suggestions[add_to_source]["count"] += 1
                source_suggestions[add_to_source][
                    "suggested_priority"
                ] = suggested_priority  # Update if higher
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


def update_preferences(preferences: Dict, changes: List[Dict]) -> Dict:
    """Applies suggested changes to the preferences."""
    updated_preferences = preferences.copy()  # Work on a copy

    for change in changes:
        if change["type"] == "add_override_rule":
            new_rule = {
                "keywords": [change["keyword"]],
                "min_priority": change["priority"],
            }
            # Check if the rule already exists
            exists = False
            for rule in updated_preferences.get("override_rules", []):
                if change["keyword"] in rule["keywords"]:
                    exists = True
                    break
            if not exists:
                updated_preferences.setdefault("override_rules", []).append(new_rule)
                print(f"  Added override rule: {new_rule}")
            else:
                print("Override rule already exists")
        elif change["type"] == "adjust_weight":
            print(
                "Weight adjustment is only a suggestion, not automatically applied. Manual adjustment recommended"
            )
    return updated_preferences


def main():
    """Processes feedback and updates preferences."""
    conn = init_db(CLASSIFIER_DB)
    try:
        feedback_data = load_feedback(conn)
        preferences = load_preferences(conn)
    
        # Get unprocessed emails from classifier DB
        opportunities = conn.execute(f"""
        SELECT 
            ea.msg_id, 
            ea.subject, 
            ea.priority, 
            ea.from_address, 
            ea.snippet,
            COUNT(*) OVER (PARTITION BY ea.from_address) AS total_from_sender
        FROM classifier_db.email_analyses ea
        LEFT JOIN feedback fb ON ea.msg_id = fb.msg_id
        WHERE fb.msg_id IS NULL
        ORDER BY 
            total_from_sender DESC,
            ea.analysis_date DESC
        LIMIT 50
    """).fetchall()
    
        # One-time migration of existing JSON data
        if not feedback_data and os.path.exists("feedback.json"):
            print("Migrating existing feedback.json to database...")
            with open("feedback.json") as f:
                legacy_feedback = json.load(f)
                save_feedback(conn, legacy_feedback)
            os.rename("feedback.json", "feedback.json.bak")
        feedback_data = legacy_feedback
    
        if not preferences.get("priority_map") and os.path.exists("email_preferences.json"):
        print("Migrating email_preferences.json to database...")
        with open("email_preferences.json") as f:
            legacy_prefs = json.load(f)
            save_preferences(conn, legacy_prefs)
            os.rename("email_preferences.json", "email_preferences.json.bak")
        preferences = legacy_prefs

    # --- Interactive Feedback Input ---
    new_feedback_entries = []
    if opportunities:
        from collections import defaultdict
        sender_groups = defaultdict(list)
        for opp in opportunities:
            sender_groups[opp[3]].append(opp)  # Group by from_address

        print(f"\nFound {len(opportunities)} emails from {len(sender_groups)} senders:")
        
        for sender_idx, (from_addr, emails) in enumerate(sender_groups.items(), 1):
            print(f"\n=== Sender {sender_idx}/{len(sender_groups)}: {from_addr} ===")
            
            # Show first 3 emails, then prompt if they want to see more
            for idx, email in enumerate(emails[:3], 1):
                msg_id, subject, priority, _, snippet, total_from_sender = email
                print(f"\n  Email {idx}: {subject}")
                print(f"  Priority: {priority}")
                print(f"  Snippet: {snippet[:100]}...")

            if len(emails) > 3:
                show_more = input(f"\n  This sender has {len(emails)} emails. Show all? (y/n/q): ").strip().lower()
                if show_more == 'q':
                    break
                if show_more == 'y':
                    for idx, email in enumerate(emails[3:], 4):
                        msg_id, subject, priority, _, snippet = email
                        print(f"\n  Email {idx}: {subject}")
                        print(f"  Priority: {priority}")
                        print(f"  Snippet: {snippet[:100]}...")

            for email in emails:
                msg_id, subject, priority, _, snippet, total_from_sender = email
                user_input = input("\nType feedback, 't' to tag, 'i' for ingest, or 'q' to quit: ").strip().lower()
                
                if user_input in ('q', 'quit'):
                    print("\nExiting feedback session...")
                    return
                
                feedback_text = ""
                action = ""
                
                if user_input == 't':
                    feedback_text = "USER ACTION: Tag for follow-up"
                    action = "follow-up"
                elif user_input == 'i':
                    print("\nSelect ingestion type:")
                    print("  1) Form submission (questions, contact requests)")
                    print("  2) Contact record update")
                    print("  3) Task creation")
                    ingest_type = input("Enter number (1-3): ").strip()
                    if ingest_type == '1':
                        feedback_text = "USER ACTION: Tag for form submission ingestion"
                        action = "form_submission"
                    elif ingest_type == '2':
                        feedback_text = "USER ACTION: Tag for contact record update"
                        action = "contact_update" 
                    elif ingest_type == '3':
                        feedback_text = "USER ACTION: Tag for task creation"
                        action = "task_creation"
                    else:
                        feedback_text = "USER ACTION: Tag for automated ingestion (unspecified type)"
                        action = "automated-ingestion"
                else:
                    feedback_text = user_input
                
                if not feedback_text:
                    continue
                    
                print("\nAvailable actions:")
                print("  - Enter priority (0-4)")
                print("  - 't' = Tag for follow-up")
                print("  - 'i' = Tag for automated ingestion")
                print("  - 'q' = Quit and save progress")
                
                suggested_priority = input("Suggested priority (0-4, blank to keep current): ").strip()
            try:
                feedback_entry = generate_feedback_json(
                    feedback_text, msg_id, subject, priority
                )
                if feedback_entry:
                    new_feedback_entries.append(feedback_entry)
                    # Save after each entry in case of interruption
                    save_feedback(conn, [feedback_entry])
            except Exception as e:
                print(f"Error processing feedback: {str(e)}")
                print("Saving partial feedback...")
                save_feedback(conn, new_feedback_entries)

    if not feedback_data and not new_feedback_entries:
        print("No existing feedback found. You can add new feedback entries.")
        while True:
            add_more = input("\nWould you like to add new feedback? (y/n): ").lower()
            if add_more != 'y':
                break
                
            feedback_text = input("\nEnter your feedback comments: ").strip()
            suggested_priority = input("Suggested priority (0-5, leave blank if unsure): ").strip()
            subject = input("Email subject (optional): ").strip() or "No Subject"
            
            # Generate unique ID based on timestamp
            msg_id = f"user_fb_{int(time.time())}"
            assigned_priority = 3  # Default neutral priority
            
            feedback_json = generate_feedback_json(
                feedback_text,
                msg_id,
                subject,
                assigned_priority
            )
            if feedback_json and not feedback_json.get("error"):
                new_feedback_entries.append(feedback_json)
                print("Feedback added successfully!")
            else:
                error_reason = feedback_json.get("error", "Unknown error") if feedback_json else "Empty response"
                print(f"Failed to process feedback entry. Reason: {error_reason}")
                print(f"Original feedback text: {feedback_text[:100]}...")
    else:
        # Process existing feedback entries that lack comments
        for entry in feedback_data:
            if "feedback_comments" not in entry or entry["feedback_comments"] == "":
                msg_id = entry["msg_id"]
                subject = entry["subject"]
                assigned_priority = entry["assigned_priority"]

                print(
                    f"\nEmail: {subject} (ID: {msg_id}, Assigned Priority: {assigned_priority})"
                )
                feedback_text = input("Enter your feedback: ")
                suggested_priority = input("Suggested priority (0-5, leave blank if unsure): ").strip()
                assigned_priority = 3  # Default neutral priority

                feedback_json = generate_feedback_json(
                    feedback_text, msg_id, subject, assigned_priority
                )
                if feedback_json:
                    new_feedback_entries.append(feedback_json)
                else:
                    print("Skipping feedback entry due to processing error.")

    # combine old and new feedback
    combined_feedback = feedback_data
    for entry in new_feedback_entries:
        # Find the matching entry in feedback_data and update it, or add as new.
        found = False
        for i, existing_entry in enumerate(feedback_data):
            if existing_entry["msg_id"] == entry["msg_id"]:
                combined_feedback[i] = entry  # update to combined
                found = True
                break
        if not found:
            combined_feedback.append(entry)

    # --- Feedback Processing ---
    if not combined_feedback:
        print("No feedback data available to process.")
        return

    print(f"Processing {len(combined_feedback)} feedback entries...")
    suggested_changes = suggest_rule_changes(combined_feedback, preferences)

    if suggested_changes:
        print("\nSuggested Changes to email_preferences.json:")
        for change in suggested_changes:
            print(
                f"- {change['type']}: {change.get('keyword', change.get('score_name'))}, Reason: {change['reason']}"
            )

        #  Uncomment the following lines to *automatically* apply the changes.
        # updated_preferences = update_preferences(preferences, suggested_changes)
        # save_preferences(conn, updated_preferences)
        # print("\nPreferences updated in database")

    else:
        print("\nNo changes suggested.")
    # Save combined feedback to database
    save_feedback(conn, combined_feedback)
    finally:
        # Clean up resources
        if conn:
            conn.execute("DETACH classifier_db") if CLASSIFIER_DB else None
            conn.close()
    print(f"Data saved to {DB_FILE}")


if __name__ == "__main__":
    main()