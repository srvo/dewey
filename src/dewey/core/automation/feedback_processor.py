import json
import os
import sys
import time
from collections import Counter
from typing import Dict, List, Tuple

import duckdb

from dewey.core.base_script import BaseScript
from dewey.core.db import DatabaseConnection


class FeedbackProcessor(BaseScript):
    """Processes feedback and suggests changes to preferences."""

    def __init__(self) -> None:
        """Initializes the FeedbackProcessor."""
        super().__init__(
            name="FeedbackProcessor",
            description="Processes feedback and suggests changes to preferences.",
            config_section="feedback_processor",
            requires_db=True,
            enable_llm=True,
        )
        self.active_data_dir = self.get_config_value("paths.data_dir", "data")
        # Ensure paths are properly constructed
        data_dir = self.get_path(self.active_data_dir)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.db_file = str(data_dir / "process_feedback.duckdb")
        self.classifier_db = str(data_dir / "email_classifier.duckdb")
        self.llm_client = None

        # Check if MotherDuck options are passed via command line
        if "--use-motherduck" in sys.argv:
            self.use_motherduck = True
        else:
            self.use_motherduck = self.get_config_value("use_motherduck", True)

        # Check for motherduck_db argument
        motherduck_db = None
        try:
            if "--motherduck-db" in sys.argv:
                idx = sys.argv.index("--motherduck-db")
                if idx + 1 < len(sys.argv):
                    motherduck_db = sys.argv[idx + 1]
        except Exception:
            pass

        if motherduck_db:
            self.motherduck_db = motherduck_db
        else:
            self.motherduck_db = self.get_config_value("motherduck_db", "dewey")

    def generate_json(self, prompt, api_key=None, llm_client=None):
        """Generate a structured JSON response from the LLM.

        Args:
            prompt (str): The prompt to send to the LLM
            api_key (str, optional): API key for LLM service
            llm_client (LiteLLMClient, optional): An existing LLM client instance

        Returns:
            dict: The structured JSON response or None if there was an error

        """
        try:
            client = None
            if llm_client:
                client = llm_client
            elif api_key:
                # Initialize the LLM client with the provided API key
                from dewey.llm.litellm_client import LiteLLMClient, LiteLLMConfig

                config = LiteLLMConfig(api_key=api_key, model="gpt-4-1106-preview")
                client = LiteLLMClient(config=config)
            elif self.llm_client:
                client = self.llm_client
            else:
                self.logger.warning(
                    "No LLM client or API key provided, unable to generate JSON"
                )
                return None

            from litellm import Message

            message = [
                Message(
                    role="system",
                    content="You are a helpful assistant that responds in JSON format.",
                ),
                Message(role="user", content=prompt),
            ]

            response = client.completion(
                messages=message,
                model="gpt-4-1106-preview",
                response_format={"type": "json_object"},
            )

            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                import json

                return json.loads(content)
            else:
                self.logger.warning("No valid response received from LLM")
                return None

        except Exception as e:
            self.logger.error(f"Error generating JSON from LLM: {e}")
            return None

    def _create_email_tables(self, conn: DatabaseConnection) -> None:
        """Create the email_analyses table if it doesn't exist."""
        try:
            # Use different schema syntax depending on whether we're using MotherDuck or local DB
            if self.use_motherduck:
                # For MotherDuck, use the database name directly
                table_prefix = ""
            else:
                # For local DB, use the attached database name
                table_prefix = "classifier_db."

            # Check if the email_analyses table exists
            if self.use_motherduck:
                exists = conn.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'email_analyses')"
                ).fetchone()[0]
            else:
                # For local database with attachment
                exists = conn.execute(
                    "SELECT EXISTS (SELECT 1 FROM classifier_db.sqlite_master WHERE type='table' AND name='email_analyses')"
                ).fetchone()[0]

            # Create the table if it doesn't exist
            if not exists:
                self.logger.info("Creating email_analyses table")
                conn.execute(f"""
                CREATE TABLE {table_prefix}email_analyses (
                    msg_id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    subject TEXT,
                    from_address TEXT,
                    priority INTEGER,
                    snippet TEXT,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

            # Add a few test emails if none exist
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table_prefix}email_analyses"
            ).fetchone()[0]
            if count == 0:
                self.logger.info("No emails found in database, adding some test data")
                # Add a variety of test emails from different senders and categories
                conn.execute(f"""
                INSERT INTO {table_prefix}email_analyses
                (msg_id, thread_id, subject, from_address, priority, snippet, analysis_date)
                VALUES
                ('work1', 'thread1', 'Project Update: Q2 Roadmap', 'manager@company.com', 3, 'Here is the updated roadmap for Q2. Please review the milestones and provide feedback by Friday.', CURRENT_TIMESTAMP),
                ('work2', 'thread2', 'Meeting Notes - Product Team', 'team-leader@company.com', 2, 'Attached are the notes from yesterday''s product meeting. Key action items highlighted.', CURRENT_TIMESTAMP),
                ('work3', 'thread3', 'Urgent: Server Downtime Alert', 'alerts@monitoring.com', 4, 'Our monitoring system has detected high load on production servers. Immediate action required.', CURRENT_TIMESTAMP),
                ('news1', 'thread4', 'Weekly Newsletter: Tech Industry Updates', 'newsletter@techupdates.com', 1, 'This week in tech: Apple announces new products, Google updates search algorithm, and more.', CURRENT_TIMESTAMP),
                ('news2', 'thread5', 'Daily Digest: Financial News', 'news@finance-updates.com', 1, 'Market summary: S&P 500 up 1.2%, NASDAQ down 0.3%. Top stories include quarterly earnings reports.', CURRENT_TIMESTAMP),
                ('personal1', 'thread6', 'Dinner next week?', 'friend@personal.com', 2, 'Would you be available for dinner next Tuesday? We could try that new restaurant downtown.', CURRENT_TIMESTAMP),
                ('receipt1', 'thread7', 'Your Amazon Order Has Shipped', 'orders@amazon.com', 1, 'Your order #12345 has shipped and is expected to arrive on Thursday. Track your package here.', CURRENT_TIMESTAMP),
                ('marketing1', 'thread8', 'Special Offer: 25% Off Summer Collection', 'marketing@retailer.com', 0, 'Summer sale starts now! Take 25% off all summer items with code SUMMER25 at checkout.', CURRENT_TIMESTAMP),
                ('work4', 'thread9', 'Code Review Request: New Feature', 'developer@company.com', 3, 'I''ve completed the new user authentication feature. Could you review my pull request when you have time?', CURRENT_TIMESTAMP),
                ('important1', 'thread10', 'Contract Renewal: Urgent Action Required', 'legal@partner.com', 4, 'The service contract expires in 10 days. We need your decision on renewal terms by Monday.', CURRENT_TIMESTAMP)
                """)
                self.logger.info(
                    f"Added 10 test emails to {table_prefix}email_analyses"
                )

                # Add different types of topics to support tagging
                self.logger.info("Creating sample topics in preferences table")
                default_preferences = {
                    "weight": {
                        "topic": 0.3,
                        "sender": 0.3,
                        "content_value": 0.2,
                        "sender_history": 0.2,
                    },
                    "topic_list": [
                        "work",
                        "personal",
                        "newsletter",
                        "receipt",
                        "marketing",
                        "urgent",
                        "finance",
                        "tech",
                        "project",
                    ],
                    "sender_list": [
                        "company.com",
                        "amazon.com",
                        "newsletter@techupdates.com",
                        "alerts@monitoring.com",
                        "marketing@retailer.com",
                    ],
                    "override_rules": [],
                }

                # Save default preferences with sample topics if not exists
                exists = conn.execute(
                    "SELECT COUNT(*) FROM preferences WHERE key = 'email_preferences'"
                ).fetchone()[0]

                if not exists:
                    self.save_preferences(conn, default_preferences)
        except Exception as e:
            self.logger.error(f"Error creating email tables: {e}")

    def init_db(self, classifier_db_path: str = "") -> DatabaseConnection:
        """Initialize the database for feedback processing."""
        try:
            # First try to connect to MotherDuck
            if self.use_motherduck:
                try:
                    self.logger.info("Attempting to connect to MotherDuck database")
                    # Get token from environment or config
                    token = os.environ.get("MOTHERDUCK_TOKEN") or self.get_config_value(
                        "motherduck_token"
                    )
                    if not token:
                        self.logger.warning(
                            "MotherDuck token not found in environment or config"
                        )
                        self.use_motherduck = False
                    else:
                        # Format the connection string properly
                        connection_string = f"md:{self.motherduck_db}"
                        os.environ["MOTHERDUCK_TOKEN"] = token
                        conn = duckdb.connect(connection_string)
                        self.logger.info(
                            f"Connected to MotherDuck database: {self.motherduck_db}"
                        )

                        # Create feedback tables if they don't exist
                        self._create_feedback_tables(conn)

                        # Connect to the classifier database in MotherDuck
                        if not classifier_db_path:
                            # If no explicit path is provided, use remote classifier DB
                            try:
                                # Check if email_analyses table exists in MotherDuck
                                exists = conn.execute(
                                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'email_analyses')"
                                ).fetchone()[0]

                                if exists:
                                    self.logger.info(
                                        "Found email_analyses table in MotherDuck"
                                    )
                                    self.classifier_db = (
                                        None  # No need for local attachment
                                    )
                                else:
                                    # Create email_analyses table in MotherDuck
                                    self._create_email_tables(conn)
                                    self.logger.info(
                                        "Created email_analyses table in MotherDuck"
                                    )
                            except Exception as e:
                                self.logger.warning(
                                    f"Error checking email_analyses table in MotherDuck: {e}"
                                )
                                # Fall back to local DB
                                self.use_motherduck = False

                        return conn

                except Exception as e:
                    self.logger.warning(f"Failed to connect to MotherDuck: {e}")
                    self.logger.warning("Falling back to local database")
                    self.use_motherduck = False

            # Fall back to local database if MotherDuck not available or not configured
            self.logger.info(f"Using local database: {self.db_file}")
            conn = duckdb.connect(self.db_file)

            # Create feedback tables
            self._create_feedback_tables(conn)

            # Connect to classifier DB
            if classifier_db_path:
                self.classifier_db = classifier_db_path

            try:
                # Try to attach the classifier database
                if self.classifier_db:
                    conn.execute(f"ATTACH '{self.classifier_db}' AS classifier_db")
                    self.logger.info(
                        f"Attached classifier database: {self.classifier_db}"
                    )

                # Create or verify the email_analyses table exists
                self._create_email_tables(conn)
                self.logger.info(
                    "Created or verified email_analyses table exists in classifier_db"
                )
            except Exception as e:
                self.logger.error(f"Error creating email tables: {e}")

            return conn

        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def _create_feedback_tables(self, conn: DatabaseConnection) -> None:
        """Create feedback and preferences tables if they don't exist.

        Args:
            conn: Database connection

        """
        try:
            # Create feedback table
            conn.execute(
                """
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
            """
            )

            # Create preferences table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    key VARCHAR PRIMARY KEY,
                    config JSON
                )
            """
            )

            # Add indexes for common queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS feedback_timestamp_idx
                ON feedback(timestamp)
            """
            )

            self.logger.info("Created or verified feedback tables")
        except Exception as e:
            self.logger.error(f"Error creating feedback tables: {e}")
            raise

    def load_feedback(self, conn: DatabaseConnection) -> list[dict]:
        """Load feedback entries from database.

        Args:
            conn: Database connection object.

        Returns:
            List of feedback entries.

        """
        result = conn.execute("SELECT * FROM feedback").fetchall()
        columns = [
            col[0] for col in conn.execute("SELECT * FROM feedback LIMIT 0").description
        ]
        return [dict(zip(columns, row)) for row in result]

    def load_preferences(self, conn: DatabaseConnection) -> dict:
        """Load preferences from database.

        Args:
            conn: Database connection object.

        Returns:
            Dictionary of preferences.

        """
        # Default preferences
        default_preferences = {
            "weight": {
                "topic": 0.3,
                "sender": 0.3,
                "content_value": 0.2,
                "sender_history": 0.2,
            },
            "topic_list": [],
            "sender_list": [],
            "override_rules": [],
        }

        try:
            result = conn.execute(
                "SELECT config FROM preferences WHERE key = 'email_preferences'"
            ).fetchone()

            if result:
                config_json = result[0]
                return json.loads(config_json)
            else:
                # Store default preferences if none found
                self.save_preferences(conn, default_preferences)
                return default_preferences
        except Exception as e:
            self.logger.error(f"Error loading preferences: {e}")
            return default_preferences

    def save_feedback(
        self, conn: DatabaseConnection, feedback_data: list[dict]
    ) -> None:
        """Save feedback entries to database.

        Args:
            conn: Database connection object.
            feedback_data: List of feedback entries.

        """
        for item in feedback_data:
            try:
                # Check if this feedback already exists
                exists = conn.execute(
                    "SELECT COUNT(*) FROM feedback WHERE msg_id = ?", [item["msg_id"]]
                ).fetchone()[0]

                if exists:
                    # Update existing record
                    conn.execute(
                        """
                        UPDATE feedback
                        SET subject = ?,
                            assigned_priority = ?,
                            feedback_comments = ?,
                            suggested_priority = ?,
                            add_to_topics = ?,
                            add_to_source = ?,
                            timestamp = ?
                        WHERE msg_id = ?
                        """,
                        [
                            item.get("subject", ""),
                            item.get("assigned_priority", 0),
                            item.get("feedback_comments", ""),
                            item.get("suggested_priority", 0),
                            item.get("add_to_topics", []),
                            item.get("add_to_source", ""),
                            item.get("timestamp", time.time()),
                            item["msg_id"],
                        ],
                    )
                else:
                    # Insert new record
                    conn.execute(
                        """
                        INSERT INTO feedback (
                            msg_id, subject, assigned_priority, feedback_comments,
                            suggested_priority, add_to_topics, add_to_source, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            item["msg_id"],
                            item.get("subject", ""),
                            item.get("assigned_priority", 0),
                            item.get("feedback_comments", ""),
                            item.get("suggested_priority", 0),
                            item.get("add_to_topics", []),
                            item.get("add_to_source", ""),
                            item.get("timestamp", time.time()),
                        ],
                    )
            except Exception as e:
                self.logger.error(f"Error saving feedback: {e}")

    def save_preferences(self, conn: DatabaseConnection, preferences: dict) -> None:
        """Save preferences to database.

        Args:
            conn: Database connection object.
            preferences: Dictionary of preferences.

        """
        try:
            # Convert preferences to JSON string
            config_json = json.dumps(preferences)

            # Check if preferences already exist
            exists = conn.execute(
                "SELECT COUNT(*) FROM preferences WHERE key = 'email_preferences'"
            ).fetchone()[0]

            if exists:
                # Update existing preferences
                conn.execute(
                    "UPDATE preferences SET config = ? WHERE key = 'email_preferences'",
                    [config_json],
                )
            else:
                # Insert new preferences
                conn.execute(
                    "INSERT INTO preferences (key, config) VALUES (?, ?)",
                    ["email_preferences", config_json],
                )
        except Exception as e:
            self.logger.error(f"Error saving preferences: {e}")

    def generate_feedback_json(
        self,
        feedback_text: str,
        msg_id: str,
        subject: str,
        assigned_priority: int,
        llm_client=None,
        deepinfra_api_key: str = None,
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
                "timestamp": time.time(),
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
    "msg_id": "auto-generated-id", "subject": "optional description", "assigned_priority": 0, "feedback_comments": "cleaned feedback summary", "suggested_priority": null, "add_to_topics": null, "add_to_source": null, "timestamp": 1710300000.123
}}

Key requirements:
1. DO NOT use code formatting (remove any ```json or ``` markers)
2. ALL output must be valid JSON - no comments, code examples or explanations
3. All fields MUST use the exact names shown above
4. JSON must be plain text - never wrapped in code blocks
5. If any field can't be determined, use `null`

Failure to follow these requirements will cause critical system errors. Always return pure JSON.
"""
        # deepinfra_api_key = self.get_config_value("llm.providers.deepinfra.api_key")
        if not deepinfra_api_key:
            self.logger.error("DEEPINFRA_API_KEY environment variable not set")
            self.logger.error("1. Get your API key from https://deepinfra.com")
            self.logger.error("2. Run: export DEEPINFRA_API_KEY='your-key-here'")
            return {}

        try:
            response_content = self.generate_json(prompt, deepinfra_api_key, llm_client)
            try:
                feedback_json = json.loads(response_content.strip())
                feedback_json["timestamp"] = time.time()
                return feedback_json
            except json.JSONDecodeError as e:
                error_msg = f"API response was not valid JSON: {str(e)}\nResponse Text: {response_content[:200]}"
                self.logger.error(f"Error: {error_msg}")
                return {"error": error_msg, "feedback_text": feedback_text}
        except Exception as e:
            self.logger.error(f"Error calling AI API: {e}")
            self.logger.error("Check your DEEPINFRA_API_KEY and internet connection")
            return {}

    def suggest_rule_changes(
        self, feedback_data: list[dict], preferences: dict
    ) -> list[dict]:
        """Analyzes feedback and suggests changes to preferences.

        Args:
            feedback_data: List of feedback entries.
            preferences: Dictionary of preferences.

        Returns:
            List of suggested changes.

        """
        suggested_changes = []
        feedback_count = len(feedback_data)

        # Minimum feedback count before suggestions are made
        if feedback_count < 5:
            self.logger.info("Not enough feedback data to suggest changes.")
            return []

        # 1. Analyze Feedback Distribution
        priority_counts = Counter(entry["assigned_priority"] for entry in feedback_data)
        self.logger.info(f"Priority Distribution in Feedback: {priority_counts}")

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
            if (
                assigned_priority != suggested_priority
                and suggested_priority is not None
            ):
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
        self.logger.info(
            f"\nMost Common Discrepancies: {discrepancy_counts.most_common()}"
        )

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

    def update_preferences(self, preferences: dict, changes: list[dict]) -> dict:
        """Applies suggested changes to the preferences.

        Args:
            preferences: Dictionary of preferences.
            changes: List of suggested changes.

        Returns:
            Updated dictionary of preferences.

        """
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
                    updated_preferences.setdefault("override_rules", []).append(
                        new_rule
                    )
                    self.logger.info(f"  Added override rule: {new_rule}")
                else:
                    self.logger.info("Override rule already exists")
            elif change["type"] == "adjust_weight":
                self.logger.info(
                    "Weight adjustment is only a suggestion, not automatically applied. Manual adjustment recommended"
                )
        return updated_preferences

    def _get_opportunities(
        self, conn: DatabaseConnection, table_prefix: str = "classifier_db."
    ) -> list[tuple]:
        """Get emails that need feedback."""
        try:
            # Query recently processed emails from the classifier DB
            query = f"""
            SELECT msg_id, thread_id, subject, from_address, priority, snippet
            FROM {table_prefix}email_analyses
            ORDER BY from_address, subject
            LIMIT 100
            """

            results = conn.execute(query).fetchall()

            if not results:
                self.logger.info("No emails found in the classifier database")
                return []

            self.logger.info(
                f"\nFound {len(results)} emails from {len({r[3] for r in results})} senders:"
            )
            return results

        except Exception as e:
            self.logger.error(f"Error getting emails for feedback: {e}")
            return []

    def _process_interactive_feedback(
        self, conn: DatabaseConnection, opportunities: list[tuple]
    ) -> list[dict]:
        """Process email feedback interactively.

        Args:
            conn: Database connection
            opportunities: List of email tuples (msg_id, thread_id, subject, from_address, priority, snippet)

        Returns:
            List of feedback dictionaries

        """
        if not opportunities:
            self.logger.info("No emails to process for feedback.")
            return []

        # Print help information
        self._print_feedback_help()

        # Group emails by sender
        emails_by_sender = {}
        for email in opportunities:
            # Make sure we have a proper tuple with expected indices
            if not isinstance(email, (list, tuple)) or len(email) < 6:
                self.logger.warning(f"Skipping invalid email record: {email}")
                continue

            # Get email data
            msg_id = email[0]
            thread_id = email[1]
            subject = email[2]
            sender = email[3]
            priority = email[4] if len(email) > 4 else 3  # Default to medium priority
            snippet = email[5] if len(email) > 5 else ""

            if sender not in emails_by_sender:
                emails_by_sender[sender] = []

            emails_by_sender[sender].append(
                {
                    "msg_id": msg_id,
                    "thread_id": thread_id,
                    "subject": subject,
                    "priority": priority,
                    "snippet": snippet,
                }
            )

        # Process emails by sender
        feedback_entries = []
        sender_count = len(emails_by_sender)

        for i, (sender, emails) in enumerate(emails_by_sender.items(), 1):
            self.logger.info(f"\n=== Sender {i}/{sender_count}: {sender} ===")

            for j, email in enumerate(emails, 1):
                self.logger.info(f"\n  Email {j}: {email['msg_id']}")
                self.logger.info(f"  Priority: {email['priority']}: {email['subject']}")
                if email["snippet"]:
                    self.logger.info(f"  Snippet: {email['snippet']}")

                # Get feedback
                while True:
                    try:
                        feedback = input("  Feedback (0-4/t/i/r/s/q/h): ").strip()

                        # Check for quit
                        if feedback.lower() in ("q", "quit"):
                            return feedback_entries

                        # Check for help
                        if feedback.lower() in ("h", "?", "help"):
                            self._print_feedback_help()
                            continue

                        # Check for skip
                        if feedback.lower() in ("s", "skip"):
                            break

                        # Check for priority
                        if feedback in ("0", "1", "2", "3", "4"):
                            priority = int(feedback)
                            feedback_entries.append(
                                {
                                    "msg_id": email["msg_id"],
                                    "subject": email["subject"],
                                    "original_priority": email["priority"],
                                    "assigned_priority": priority,
                                    "feedback_comments": f"Priority changed to {priority}",
                                    "timestamp": time.time(),
                                }
                            )
                            self.logger.info(f"  Priority set to {priority}")
                            break

                        # Check for tagging
                        if feedback.lower() in ("t", "tag"):
                            topics = input("  Enter topics (comma-separated): ").strip()
                            if topics:
                                feedback_entries.append(
                                    {
                                        "msg_id": email["msg_id"],
                                        "subject": email["subject"],
                                        "original_priority": email["priority"],
                                        "assigned_priority": email["priority"],
                                        "add_to_topics": topics,
                                        "feedback_comments": f"Tagged with: {topics}",
                                        "timestamp": time.time(),
                                    }
                                )
                                self.logger.info(f"  Tagged with: {topics}")
                            break

                        # Check for rule
                        if feedback.lower() in ("r", "rule"):
                            rule_type = input(
                                "  Rule type (topic/sender/block): "
                            ).strip()
                            if rule_type.lower() in ("topic", "sender", "block"):
                                rule_value = input(
                                    f"  {rule_type.capitalize()} value: "
                                ).strip()
                                if rule_value:
                                    feedback_entries.append(
                                        {
                                            "msg_id": email["msg_id"],
                                            "subject": email["subject"],
                                            "original_priority": email["priority"],
                                            "assigned_priority": email["priority"],
                                            "feedback_comments": f"Create {rule_type} rule for: {rule_value}",
                                            "rule_type": rule_type,
                                            "rule_value": rule_value,
                                            "timestamp": time.time(),
                                        }
                                    )
                                    self.logger.info(
                                        f"  Created {rule_type} rule for: {rule_value}"
                                    )
                            break

                        # Check for ingest
                        if feedback.lower() in ("i", "ingest"):
                            ingest_type = input(
                                "  Ingest type (form/contact/task): "
                            ).strip()
                            if ingest_type.lower() in ("form", "contact", "task"):
                                feedback_entries.append(
                                    {
                                        "msg_id": email["msg_id"],
                                        "subject": email["subject"],
                                        "original_priority": email["priority"],
                                        "assigned_priority": email["priority"],
                                        "feedback_comments": f"Ingest as {ingest_type}",
                                        "ingest_type": ingest_type,
                                        "timestamp": time.time(),
                                    }
                                )
                                self.logger.info(
                                    f"  Marked for ingestion as: {ingest_type}"
                                )
                            break

                        # Default to comment
                        if feedback:
                            feedback_entries.append(
                                {
                                    "msg_id": email["msg_id"],
                                    "subject": email["subject"],
                                    "original_priority": email["priority"],
                                    "assigned_priority": email["priority"],
                                    "feedback_comments": feedback,
                                    "timestamp": time.time(),
                                }
                            )
                            self.logger.info(f"  Comment added: {feedback}")
                            break

                    except KeyboardInterrupt:
                        self.logger.info("\nOperation cancelled by user.")
                        return feedback_entries
                    except Exception as e:
                        self.logger.error(f"Error processing feedback: {e}")

        return feedback_entries

    def _print_feedback_help(self):
        """Print help information for the feedback processor."""
        self.logger.info("\n=== FEEDBACK HELP ===")
        self.logger.info("  0-4        Set priority (0=lowest, 4=highest)")
        self.logger.info("  t, tag     Tag email with topics")
        self.logger.info("  i, ingest  Mark for ingestion (form/contact/task)")
        self.logger.info("  r, rule    Create rule for this sender")
        self.logger.info("  s, skip    Skip this email")
        self.logger.info("  q, quit    Quit and save progress")
        self.logger.info("  h, ?       Show this help")
        self.logger.info("  [text]     Add a comment")
        self.logger.info("======================")

    def execute(self) -> None:
        """Execute the feedback processor.

        This implementation satisfies the abstract method requirement from BaseScript.
        Delegates to the run method for actual implementation.
        """
        try:
            self.logger.info(f"Starting execution of {self.name}")
            self.run()
            self.logger.info(f"Successfully completed feedback processing")
        except Exception as e:
            self.logger.error(f"Error executing feedback processor: {e}", exc_info=True)
            raise

    def run(self) -> None:
        """Run the feedback processor."""
        conn = None
        try:
            # Initialize database connection
            conn = self.init_db()

            # Log the type of database being used
            if self.use_motherduck:
                self.logger.info(f"Using MotherDuck database: {self.motherduck_db}")
            else:
                self.logger.info("Using local database")

            # Define table prefix based on database type
            table_prefix = "" if self.use_motherduck else "classifier_db."

            # Load existing feedback and preferences
            existing_feedback = self.load_feedback(conn)
            preferences = self.load_preferences(conn)

            # Handle JSON to database migration if found
            self._maybe_migrate_json_to_db(conn, existing_feedback, preferences)

            # Get email data from classifier database
            opportunities = self._get_opportunities(conn, table_prefix)

            if not opportunities:
                self.logger.info(
                    "No emails found for feedback. Please run the email classifier first."
                )
                return

            # Print help information
            self._print_feedback_help()

            # Process feedback interactively
            new_feedback = self._process_interactive_feedback(conn, opportunities)

            if new_feedback:
                # Combine old and new feedback
                all_feedback = existing_feedback + new_feedback

                # Save the feedback
                self.save_feedback(conn, all_feedback)

                # Suggest rule changes based on feedback
                rule_changes = self.suggest_rule_changes(all_feedback, preferences)

                # If there are suggested changes, update preferences
                if rule_changes:
                    preferences = self.update_preferences(preferences, rule_changes)
                    self.save_preferences(conn, preferences)

                # Ensure MotherDuck sync if using MotherDuck
                if self.use_motherduck:
                    # Execute a simple query to ensure data is committed to MotherDuck
                    conn.execute("SELECT 1")
                    self.logger.info("Data synchronized with MotherDuck")
            else:
                self.logger.info("No new feedback collected. Exiting.")

        except KeyboardInterrupt:
            self.logger.info("\nOperation cancelled by user. Saving progress...")
            if conn:
                try:
                    # Ensure data is committed before exiting
                    conn.execute("SELECT 1")
                except Exception as e:
                    self.logger.warning(f"Error committing data: {e}")
        except Exception as e:
            self.logger.error(f"Error during feedback processing: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
        finally:
            # Close database connection
            if conn:
                try:
                    if self.classifier_db:
                        try:
                            # Detach classifier DB if attached
                            conn.execute("DETACH classifier_db")
                            self.logger.debug("Detached classifier database")
                        except Exception as e:
                            self.logger.debug(
                                f"Error detaching classifier database: {e}"
                            )

                    # Close connection
                    conn.close()
                    self.logger.debug("Closed database connection")
                except Exception as e:
                    self.logger.debug(f"Error closing database connection: {e}")

    def _maybe_migrate_json_to_db(
        self, conn: DatabaseConnection, existing_feedback: list[dict], preferences: dict
    ) -> None:
        """Migrate data from JSON files to database if needed."""
        # Check if there's existing data in the DB
        if existing_feedback or preferences:
            return

        # Check for JSON files
        data_dir = self.get_path(self.active_data_dir)
        feedback_file = data_dir / "feedback.json"
        prefs_file = data_dir / "email_preferences.json"

        # Migrate feedback data
        if feedback_file.exists():
            try:
                with open(feedback_file) as f:
                    feedback_data = json.load(f)
                    if feedback_data:
                        self.logger.info(
                            f"Migrating feedback data from {feedback_file}"
                        )
                        self.save_feedback(conn, feedback_data)
            except Exception as e:
                self.logger.warning(f"Error migrating feedback data: {e}")

        # Migrate preferences data
        if prefs_file.exists():
            try:
                with open(prefs_file) as f:
                    prefs_data = json.load(f)
                    if prefs_data:
                        self.logger.info(
                            f"Migrating preferences data from {prefs_file}"
                        )
                        self.save_preferences(conn, prefs_data)
            except Exception as e:
                self.logger.warning(f"Error migrating preferences data: {e}")


if __name__ == "__main__":
    FeedbackProcessor().execute()
