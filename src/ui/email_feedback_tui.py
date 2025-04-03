#!/usr/bin/env python3
"""TUI for feedback processing using charmbracelet/gum"""

import json
import os
import subprocess
import time
from collections import Counter
from typing import Dict, List

import duckdb

# Reuse existing DB config from process_feedback.py
ACTIVE_DATA_DIR = "/Users/srvo/input_data/ActiveData"
DB_FILE = f"{ACTIVE_DATA_DIR}/process_feedback.duckdb"
CLASSIFIER_DB = f"{ACTIVE_DATA_DIR}/email_classifier.duckdb"


def get_feedback_stats(conn) -> dict:
    """Get statistics about feedback data"""
    stats = conn.execute(
        """
        SELECT
            COUNT(*) as total,
            AVG(suggested_priority) as avg_priority,
            COUNT(DISTINCT add_to_source) as unique_sources
        FROM feedback
    """
    ).fetchone()

    return {
        "total": stats[0],
        "avg_priority": round(stats[1], 1) if stats[1] else 0,
        "unique_sources": stats[2],
    }


def display_feedback_table(conn):
    """Show feedback entries in a gum table view"""
    feedback = conn.execute(
        """
        SELECT msg_id, subject, assigned_priority, suggested_priority,
               array_to_string(add_to_topics, ', ') as topics,
               add_to_source, datetime(timestamp) as time
        FROM feedback
        ORDER BY timestamp DESC
        LIMIT 50
    """
    ).fetchall()

    if not feedback:
        subprocess.run(["gum", "format", "-t", "emoji", "# No feedback found! :cry:"])
        return

    # Build table data
    table = ["MSG ID\tSUBJECT\tASSIGNED\tSUGGESTED\tTOPICS\tSOURCE\tTIME"]
    for row in feedback:
        table.append("\t".join(map(str, row)))

    # Show interactive table
    cmd = ["gum", "table", "--separator='\t'", "--height=20", "--width=180"]
    subprocess.run(cmd, input="\n".join(table), text=True)


def add_feedback_flow(conn):
    """Interactive feedback addition flow using gum prompts"""
    # Get email candidates for feedback
    opportunities = conn.execute(
        """
        SELECT ea.msg_id, ea.subject, ea.priority
        FROM classifier_db.email_analyses ea
        LEFT JOIN feedback fb ON ea.msg_id = fb.msg_id
        WHERE fb.msg_id IS NULL
        ORDER BY ea.analysis_date DESC
        LIMIT 100
    """
    ).fetchall()

    if not opportunities:
        subprocess.run(
            [
                "gum",
                "format",
                "-t",
                "emoji",
                "# No unprocessed emails found! :sparkles:",
            ]
        )
        return

    # Let user select an email
    email_choices = [
        f"{row[0]} - {row[1]} (Priority: {row[2]})" for row in opportunities
    ]
    selection = subprocess.run(
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
    ).stdout.strip()

    if not selection:
        return

    msg_id = selection.split(" - ")[0]
    selected_email = next(row for row in opportunities if row[0] in selection)

    # Collect feedback via gum inputs
    subprocess.run(
        [
            "gum",
            "format",
            "-t",
            "emoji",
            f"# Providing feedback for: {selected_email[1]}",
        ]
    )

    comments = subprocess.run(
        ["gum", "input", "--placeholder", "Enter your feedback comments..."],
        text=True,
        capture_output=True,
    ).stdout.strip()

    priority = subprocess.run(
        [
            "gum",
            "input",
            "--placeholder",
            "Suggested priority (0-4, leave blank if unsure)...",
        ],
        text=True,
        capture_output=True,
    ).stdout.strip()

    # Generate feedback entry
    feedback_entry = {
        "msg_id": msg_id,
        "subject": selected_email[1],
        "assigned_priority": selected_email[2],
        "feedback_comments": comments,
        "suggested_priority": int(priority) if priority.isdigit() else None,
        "add_to_topics": None,
        "add_to_source": None,
        "timestamp": None,
    }

    # Save to DB using DuckDB's UPSERT syntax
    conn.execute(
        """
        INSERT INTO feedback
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (msg_id) DO UPDATE SET
            subject = EXCLUDED.subject,
            assigned_priority = EXCLUDED.assigned_priority,
            feedback_comments = EXCLUDED.feedback_comments,
            suggested_priority = EXCLUDED.suggested_priority,
            add_to_topics = EXCLUDED.add_to_topics,
            add_to_source = EXCLUDED.add_to_source,
            timestamp = EXCLUDED.timestamp
    """,
        [
            feedback_entry["msg_id"],
            feedback_entry["subject"],
            feedback_entry["assigned_priority"],
            feedback_entry["feedback_comments"],
            feedback_entry["suggested_priority"],
            feedback_entry["add_to_topics"],
            feedback_entry["add_to_source"],
            feedback_entry["timestamp"],
        ],
    )

    subprocess.run(
        [
            "gum",
            "format",
            "-t",
            "emoji",
            "# Feedback saved! :white_check_mark:",
        ]
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
                }
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
                }
            )

    return suggested_changes


def analyze_feedback(conn):
    """Show analysis of feedback patterns"""
    # Get existing analysis logic from process_feedback.py
    feedback_data = conn.execute("SELECT * FROM feedback").fetchall()
    columns = [col[0] for col in conn.description]
    feedback = [dict(zip(columns, row)) for row in feedback_data]

    preferences = conn.execute(
        "SELECT config FROM preferences WHERE key = 'latest'"
    ).fetchone()
    preferences = json.loads(preferences[0]) if preferences else {"override_rules": []}

    suggestions = suggest_rule_changes(feedback, preferences)

    if not suggestions:
        subprocess.run(
            [
                "gum",
                "format",
                "-t",
                "emoji",
                "# No suggested changes found :magnifying_glass_tilted_left:",
            ]
        )
        return

    # Format suggestions for display
    output = ["# Suggested Rule Changes", ""]
    for change in suggestions:
        output.append(f"## {change['type'].replace('_', ' ').title()}")
        output.append(f"- **Keyword**: {change.get('keyword', 'N/A')}")
        output.append(f"- **Reason**: {change['reason']}")
        output.append(f"- **Priority**: {change.get('priority', 'N/A')}")
        output.append("")

    subprocess.run(
        ["gum", "format", "-t", "markdown"],
        input="\n".join(output),
        text=True,
    )


def main_menu():
    """Display main TUI menu"""
    try:
        # Add retry logic for database connection
        max_retries = 3
        retry_delay = 1  # seconds
        conn = None

        for attempt in range(max_retries):
            try:
                conn = duckdb.connect(DB_FILE)
                # Check if classifier DB exists before attaching
                if not os.path.exists(CLASSIFIER_DB):
                    subprocess.run(
                        [
                            "gum",
                            "format",
                            "-t",
                            "emoji",
                            (
                                f"# Missing classifier DB! :warning:\n"
                                f"Path: {CLASSIFIER_DB}"
                            ),
                        ]
                    )
                    return

                try:
                    conn.execute(f"ATTACH '{CLASSIFIER_DB}' AS classifier_db")
                except duckdb.CatalogException:
                    pass  # Already attached

                break
            except duckdb.IOException as e:
                if "Could not set lock" in str(e) and attempt < max_retries - 1:
                    msg = f"Database locked, retrying in {retry_delay}s ({attempt + 1}/{
                        max_retries
                    })"
                    subprocess.run(
                        [
                            "gum",
                            "format",
                            "-t",
                            "emoji",
                            f"# {msg} :hourglass:",
                        ]
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

        while True:
            stats = get_feedback_stats(conn)

            choice = subprocess.run(
                [
                    "gum",
                    "choose",
                    "--header",
                    f"Feedback Stats: {stats['total']} entries | Avg Priority: {
                        stats['avg_priority']
                    } | Sources: {stats['unique_sources']}",
                    "View Feedback",
                    "Add Feedback",
                    "Analyze Patterns",
                    "Exit",
                ],
                text=True,
                capture_output=True,
            ).stdout.strip()

            if not choice or "Exit" in choice:
                break

            if "View Feedback" in choice:
                display_feedback_table(conn)
            elif "Add Feedback" in choice:
                add_feedback_flow(conn)
            elif "Analyze Patterns" in choice:
                analyze_feedback(conn)

    except Exception as e:
        error_msg = f"Database error: {
            str(e)
        }\nCheck if another process is using the database files."
        subprocess.run(
            [
                "gum",
                "format",
                "-t",
                "emoji",
                f"# Critical Error! :boom:\n{error_msg}",
            ]
        )
        print(f"\nTechnical details:\n{str(e)}")
        return
    finally:
        if conn:
            conn.close()
            subprocess.run(["gum", "format", "-t", "emoji", "# Session ended :wave:"])


if __name__ == "__main__":
    main_menu()
