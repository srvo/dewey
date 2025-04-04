#!/usr/bin/env python3
"""TUI for feedback processing using charmbracelet/gum and PostgreSQL"""

import json
import logging
import os
import subprocess
import time
from collections import Counter
from typing import Any

# Import PostgreSQL utilities
from dewey.utils.database import (
    close_pool,
    execute_query,
    fetch_all,
    fetch_one,
    initialize_pool,
)

logger = logging.getLogger(__name__)


def get_feedback_stats() -> dict[str, Any] | None:
    """Get statistics about feedback data from PostgreSQL"""
    query = """
    SELECT
        COUNT(*) as total,
        AVG(suggested_priority) as avg_priority,
        COUNT(DISTINCT add_to_source) as unique_sources
    FROM feedback
    """
    try:
        stats = fetch_one(query)
        if stats:
            return {
                "total": stats[0],
                "avg_priority": round(stats[1], 1) if stats[1] is not None else 0,
                "unique_sources": stats[2],
            }
        return None  # No stats found or error during fetch
    except Exception as e:
        logger.error(f"Error fetching feedback stats: {e}")
        return None


def display_feedback_table():
    """Show feedback entries in a gum table view from PostgreSQL"""
    query = """
    SELECT msg_id, subject, assigned_priority, suggested_priority,
           array_to_string(add_to_topics, ', ') as topics,
           add_to_source, timestamp::timestamp as time -- Ensure correct timestamp type
    FROM feedback
    ORDER BY timestamp DESC
    LIMIT 50
    """
    try:
        feedback = fetch_all(query)

        if not feedback:
            subprocess.run(
                ["gum", "format", "-t", "emoji", "# No feedback found! :cry:"],
                check=False,
            )
            return

        # Build table data
        table = ["MSG ID\tSUBJECT\tASSIGNED\tSUGGESTED\tTOPICS\tSOURCE\tTIME"]
        for row in feedback:
            # Convert None values to empty strings for display
            display_row = [str(item) if item is not None else "" for item in row]
            table.append("\t".join(display_row))

        # Show interactive table
        cmd = ["gum", "table", "--separator='\t'", "--height=20", "--width=180"]
        subprocess.run(cmd, input="\n".join(table), text=True, check=False)

    except Exception as e:
        logger.error(f"Error displaying feedback table: {e}")
        subprocess.run(
            ["gum", "format", "-t", "emoji", f"# Error loading data: {e} :warning:"],
            check=False,
        )


def add_feedback_flow():
    """Interactive feedback addition flow using PostgreSQL"""
    # Get email candidates for feedback
    # Assumes email_analyses table exists in the same PG database
    query_opportunities = """
    SELECT ea.msg_id, ea.subject, ea.priority
    FROM email_analyses ea
    LEFT JOIN feedback fb ON ea.msg_id = fb.msg_id
    WHERE fb.msg_id IS NULL
    ORDER BY ea.analysis_date DESC
    LIMIT 100
    """
    try:
        opportunities = fetch_all(query_opportunities)
    except Exception as e:
        logger.error(f"Error fetching feedback opportunities: {e}")
        subprocess.run(
            ["gum", "format", "-t", "emoji", f"# Error fetching emails: {e} :warning:"],
            check=False,
        )
        return

    if not opportunities:
        subprocess.run(
            [
                "gum",
                "format",
                "-t",
                "emoji",
                "# No unprocessed emails found! :sparkles:",
            ],
            check=False,
        )
        return

    # Let user select an email
    # Gum choice expects simple strings
    email_choices = [
        f"{row[0]} - {row[1]} (Priority: {row[2]})" for row in opportunities
    ]
    selection_process = subprocess.run(
        [
            "gum",
            "choose",
            "--height=10",
            "--header",
            "Select email to provide feedback",
        ],
        input="\n".join(email_choices),
        text=True,
        capture_output=True,
        check=False,
    )

    selection = selection_process.stdout.strip()
    if selection_process.returncode != 0 or not selection:
        logger.info("User cancelled email selection.")
        return

    # Extract msg_id reliably
    msg_id = selection.split(" - ")[0]
    try:
        selected_email = next(row for row in opportunities if row[0] == msg_id)
    except StopIteration:
        logger.error(f"Could not find selected email data for msg_id: {msg_id}")
        return

    # Collect feedback via gum inputs
    subprocess.run(
        [
            "gum",
            "format",
            "-t",
            "emoji",
            f"# Providing feedback for: {selected_email[1]}",
        ],
        check=False,
    )

    comments = subprocess.run(
        ["gum", "input", "--placeholder", "Enter your feedback comments..."],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()

    priority_input = subprocess.run(
        [
            "gum",
            "input",
            "--placeholder",
            "Suggested priority (0-4, leave blank if unsure)...",
        ],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()

    # Prepare feedback data for insertion
    feedback_data = {
        "msg_id": msg_id,
        "subject": selected_email[1],
        "original_priority": selected_email[2],  # Use original analysis priority
        "assigned_priority": selected_email[2],  # Default assigned to original
        "feedback_comments": comments,
        "suggested_priority": int(priority_input) if priority_input.isdigit() else None,
        "add_to_topics": None,  # TODO: Add gum flow for topics?
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc,
        ),  # Use timezone aware time
        "follow_up": False,
        "contact_email": None,  # TODO: Extract from email if needed?
        "contact_name": None,
        "contact_notes": None,
        # Removed add_to_source - assuming this column is removed or handled elsewhere
    }

    # Save to DB using PostgreSQL UPSERT
    # Adjust columns based on the target 'feedback' table definition used previously
    insert_query = """
    INSERT INTO feedback (
        msg_id, subject, original_priority, assigned_priority, suggested_priority,
        feedback_comments, add_to_topics, timestamp, follow_up,
        contact_email, contact_name, contact_notes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (msg_id) DO UPDATE SET
        subject = EXCLUDED.subject,
        original_priority = EXCLUDED.original_priority, # Keep original priority
        assigned_priority = EXCLUDED.assigned_priority, # Update assigned if needed
        suggested_priority = EXCLUDED.suggested_priority,
        feedback_comments = EXCLUDED.feedback_comments,
        add_to_topics = EXCLUDED.add_to_topics,
        timestamp = EXCLUDED.timestamp, # Update timestamp on conflict
        follow_up = EXCLUDED.follow_up,
        contact_email = EXCLUDED.contact_email,
        contact_name = EXCLUDED.contact_name,
        contact_notes = EXCLUDED.contact_notes
        # Ensure all columns from the VALUES clause are listed in ON CONFLICT SET
    """
    params = [
        feedback_data["msg_id"],
        feedback_data["subject"],
        feedback_data["original_priority"],
        feedback_data["assigned_priority"],
        feedback_data["suggested_priority"],
        feedback_data["feedback_comments"],
        # Convert list/None to string representation if column expects text
        json.dumps(feedback_data["add_to_topics"])
        if feedback_data["add_to_topics"]
        else None,
        feedback_data["timestamp"],
        feedback_data["follow_up"],
        feedback_data["contact_email"],
        feedback_data["contact_name"],
        feedback_data["contact_notes"],
    ]

    try:
        execute_query(insert_query, params)
        subprocess.run(
            ["gum", "format", "-t", "emoji", "# Feedback saved! :white_check_mark:"],
            check=False,
        )
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        subprocess.run(
            ["gum", "format", "-t", "emoji", f"# Error saving feedback: {e} :warning:"],
            check=False,
        )


def suggest_rule_changes(feedback: list[dict], preferences: dict) -> list[dict]:
    """Analyzes feedback and suggests changes to preferences."""
    suggested_changes = []
    feedback_count = len(feedback)

    # Minimum feedback count before suggestions are made
    if feedback_count < 5:
        return []

    # 1. Analyze Feedback Distribution
    # 2. Identify Frequent Discrepancies
    discrepancy_counts = Counter()
    topic_suggestions = {}  # Store suggested topic changes
    source_suggestions = {}

    for entry in feedback:
        if not entry:  # skip if empty
            continue

        assigned_priority = int(entry.get("assigned_priority"))
        suggested_priority = entry.get("suggested_priority")
        add_to_topics = entry.get("add_to_topics")
        add_to_source = entry.get("add_to_source")

        # Check if there is a discrepancy
        if assigned_priority != suggested_priority and suggested_priority is not None:
            discrepancy_key = (assigned_priority, suggested_priority)
            discrepancy_counts[discrepancy_key] += 1

            # Check if keywords are in topics or source
            if add_to_topics:
                for keyword in add_to_topics:
                    if keyword not in topic_suggestions:
                        topic_suggestions[keyword] = {
                            "count": 0,
                            "suggested_priority": suggested_priority,
                        }
                    topic_suggestions[keyword]["count"] += 1
                    topic_suggestions[keyword]["suggested_priority"] = (
                        suggested_priority
                    )

            if add_to_source:
                if add_to_source not in source_suggestions:
                    source_suggestions[add_to_source] = {
                        "count": 0,
                        "suggested_priority": suggested_priority,
                    }
                source_suggestions[add_to_source]["count"] += 1
                source_suggestions[add_to_source]["suggested_priority"] = (
                    suggested_priority
                )

    # 3. Suggest new override rules
    for topic, suggestion in topic_suggestions.items():
        if suggestion["count"] >= 3:
            suggested_changes.append(
                {
                    "type": "add_override_rule",
                    "keyword": topic,
                    "priority": suggestion["suggested_priority"],
                    "reason": (
                        f"Suggested based on feedback (topic appeared "
                        f"{suggestion['count']} times with consistent "
                        f"priority)"
                    ),
                },
            )

    for source, suggestion in source_suggestions.items():
        if suggestion["count"] >= 3:
            suggested_changes.append(
                {
                    "type": "add_override_rule",
                    "keyword": source,
                    "priority": suggestion["suggested_priority"],
                    "reason": (
                        f"Suggested based on feedback (source appeared "
                        f"{suggestion['count']} times with consistent "
                        f"priority)"
                    ),
                },
            )

    return suggested_changes


def analyze_feedback():
    """Placeholder for feedback analysis logic (was connecting to DB)"""
    # conn = duckdb.connect(DB_FILE)
    # feedback = conn.execute("SELECT * FROM feedback").fetchall()
    # conn.close()

    # TODO: Implement fetching feedback using fetch_all if needed for analysis
    # feedback_rows = fetch_all("SELECT * FROM feedback")
    # Convert rows to dicts if the function expects dicts

    logger.warning(
        "analyze_feedback function needs implementation using PostgreSQL utilities.",
    )
    subprocess.run(
        [
            "gum",
            "format",
            "-t",
            "emoji",
            "# Analysis feature not yet migrated :construction:",
        ],
        check=False,
    )

    # Load preferences (this part seems okay)
    try:
        with open("preferences.json") as f:
            preferences = json.load(f)
    except FileNotFoundError:
        preferences = {}

    # suggested_changes = suggest_rule_changes(feedback, preferences)
    suggested_changes = []  # Placeholder until feedback fetching is implemented

    if not suggested_changes:
        subprocess.run(
            [
                "gum",
                "format",
                "-t",
                "emoji",
                "# No suggestions based on current feedback :thinking:",
            ],
            check=False,
        )
        return

    # Display suggestions (this part seems okay)
    subprocess.run(
        ["gum", "format", "-t", "emoji", "# Suggested Preference Changes :bulb:"],
        check=False,
    )
    for change in suggested_changes:
        print(
            f"- Type: {change['type']}, Keyword/Source: {change.get('keyword') or change.get('source')}, Priority: {change['priority']}, Reason: {change['reason']}",
        )


def main_menu():
    """Main interactive menu using gum"""
    # Initialize the pool when the menu starts
    try:
        initialize_pool()
    except Exception as e:
        logger.critical(f"Failed to initialize database pool. Exiting. Error: {e}")
        print(f"Database connection error: {e}", file=sys.stderr)
        return  # Exit if pool fails

    while True:
        # Get stats (handle potential None)
        stats = get_feedback_stats()
        stats_line = "Stats: (Loading...)"  # Default message
        if stats:
            stats_line = (
                f"Total Feedback: {stats['total']} | "
                f"Avg Suggested Priority: {stats['avg_priority']} | "
                f"Unique Sources: {stats['unique_sources']}"
            )
        elif stats is None:
            stats_line = "Stats: (Error loading)"  # Indicate error

        # Show main menu
        cmd = [
            "gum",
            "choose",
            "--header",
            f"Dewey Feedback TUI - {stats_line}",
            "--height=10",
            "View Feedback Table",
            "Add Feedback",
            "Analyze Feedback & Suggest Rules",
            "Exit",
        ]
        choice = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
        ).stdout.strip()

        if choice == "View Feedback Table":
            display_feedback_table()
        elif choice == "Add Feedback":
            add_feedback_flow()
        elif choice == "Analyze Feedback & Suggest Rules":
            analyze_feedback()
        elif choice == "Exit":
            logger.info("Exiting Feedback TUI.")
            break
        else:
            # Handle empty choice or errors from gum
            logger.warning("Invalid choice or gum error.")
            time.sleep(1)
            # break # Optionally exit on error

    # Close the pool when the menu loop exits
    close_pool()


if __name__ == "__main__":
    # Basic logging setup
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.INFO,  # Changed level to INFO
        format="%Y-%m-%d %H:%M:%S - %(name)s - %(levelname)s - %(message)s",
        filename=os.path.join(log_dir, "email_feedback_tui.log"),
        filemode="a",
    )
    logger.info("Starting Email Feedback TUI")

    # Check if gum is installed
    try:
        subprocess.run(["gum", "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.critical("gum command not found. Please install charmbracelet/gum.")
        print(
            "Error: gum command not found. Please install charmbracelet/gum: https://github.com/charmbracelet/gum",
            file=sys.stderr,
        )
        sys.exit(1)  # Added sys import needed

    try:
        main_menu()
    except Exception as e:
        logger.exception("An unexpected error occurred in the main loop.")
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        # Ensure pool is closed even if main_menu crashes before its finally block
        close_pool()
        logger.info("Email Feedback TUI finished.")
