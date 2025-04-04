import json
import logging
import time
from collections import Counter

from dewey.core.base_script import BaseScript
from dewey.utils.database import (
    execute_query,
    fetch_all,
    fetch_one,
    initialize_pool,
    table_exists,
)

logger = logging.getLogger(__name__)


class FeedbackProcessor(BaseScript):
    """Processes feedback and suggests changes to preferences using PostgreSQL."""

    def __init__(self) -> None:
        """Initializes the FeedbackProcessor."""
        super().__init__(
            name="FeedbackProcessor",
            description="Processes feedback and suggests changes to preferences.",
            config_section="feedback_processor",
            requires_db=True,
            enable_llm=True,
        )
        self.llm_client = None
        initialize_pool()

    def generate_json(self, prompt, api_key=None, llm_client=None):
        """
        Generate a structured JSON response from the LLM.

        Args:
        ----
            prompt (str): The prompt to send to the LLM
            api_key (str, optional): API key for LLM service
            llm_client (LiteLLMClient, optional): An existing LLM client instance

        Returns:
        -------
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
                    "No LLM client or API key provided, unable to generate JSON",
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
            self.logger.warning("No valid response received from LLM")
            return None

        except Exception as e:
            self.logger.error(f"Error generating JSON from LLM: {e}")
            return None

    def _create_email_tables(self) -> None:
        """Create the email_analyses table if it doesn't exist in PostgreSQL."""
        table_name = "email_analyses"
        try:
            # Check if the email_analyses table exists
            if not table_exists(table_name):
                self.logger.info(f"Creating {table_name} table")
                columns_definition = (
                    "msg_id TEXT PRIMARY KEY, "
                    "thread_id TEXT, "
                    "subject TEXT, "
                    "from_address TEXT, "
                    "priority INTEGER, "
                    "snippet TEXT, "
                    "analysis_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                )
                create_query = f"CREATE TABLE {table_name} ({columns_definition})"
                execute_query(create_query)
                self.logger.info(f"Successfully created {table_name} table.")

                # Add test data if table was just created
                self._add_test_email_data(table_name)
            else:
                self.logger.debug(f"Table {table_name} already exists.")

        except Exception as e:
            self.logger.error(f"Error creating {table_name} table: {e}")
            raise

    def _add_test_email_data(self, table_name: str) -> None:
        """Adds sample email data to the specified table."""
        try:
            # Check if table is empty before inserting
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count_result = fetch_one(count_query)
            if count_result and count_result[0] == 0:
                self.logger.info(f"Table {table_name} is empty, adding test data.")
                insert_query = f"""
                INSERT INTO {table_name}
                (msg_id, thread_id, subject, from_address, priority, snippet, analysis_date)
                VALUES
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP),
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """
                params = [
                    "work1",
                    "thread1",
                    "Project Update: Q2 Roadmap",
                    "manager@company.com",
                    3,
                    "Here is the updated roadmap for Q2. Please review the milestones and provide feedback by Friday.",
                    "work2",
                    "thread2",
                    "Meeting Notes - Product Team",
                    "team-leader@company.com",
                    2,
                    "Attached are the notes from yesterday''s product meeting. Key action items highlighted.",
                    "work3",
                    "thread3",
                    "Urgent: Server Downtime Alert",
                    "alerts@monitoring.com",
                    4,
                    "Our monitoring system has detected high load on production servers. Immediate action required.",
                    "news1",
                    "thread4",
                    "Weekly Newsletter: Tech Industry Updates",
                    "newsletter@techupdates.com",
                    1,
                    "This week in tech: Apple announces new products, Google updates search algorithm, and more.",
                    "news2",
                    "thread5",
                    "Daily Digest: Financial News",
                    "news@finance-updates.com",
                    1,
                    "Market summary: S&P 500 up 1.2%, NASDAQ down 0.3%. Top stories include quarterly earnings reports.",
                    "personal1",
                    "thread6",
                    "Dinner next week?",
                    "friend@personal.com",
                    2,
                    "Would you be available for dinner next Tuesday? We could try that new restaurant downtown.",
                    "receipt1",
                    "thread7",
                    "Your Amazon Order Has Shipped",
                    "orders@amazon.com",
                    1,
                    "Your order #12345 has shipped and is expected to arrive on Thursday. Track your package here.",
                    "marketing1",
                    "thread8",
                    "Special Offer: 25% Off Summer Collection",
                    "marketing@retailer.com",
                    0,
                    "Summer sale starts now! Take 25% off all summer items with code SUMMER25 at checkout.",
                    "work4",
                    "thread9",
                    "Code Review Request: New Feature",
                    "developer@company.com",
                    3,
                    "I''ve completed the new user authentication feature. Could you review my pull request when you have time?",
                    "important1",
                    "thread10",
                    "Contract Renewal: Urgent Action Required",
                    "legal@partner.com",
                    4,
                    "The service contract expires in 10 days. We need your decision on renewal terms by Monday.",
                ]
                execute_query(insert_query, params)
                self.logger.info(f"Added 10 test emails to {table_name}")
                self._add_test_preferences()
            else:
                self.logger.debug(
                    f"Table {table_name} already contains data. Skipping test data insertion.",
                )
        except Exception as e:
            self.logger.error(f"Error adding test data to {table_name}: {e}")

    def _add_test_preferences(self) -> None:
        """Adds default preferences if the preferences table is empty."""
        pref_table = "preferences"
        pref_key = "email_preferences"
        try:
            if not table_exists(pref_table):
                self.logger.warning(
                    f"Preferences table '{pref_table}' not found. Skipping default preferences.",
                )
                return

            count_query = f"SELECT COUNT(*) FROM {pref_table} WHERE key = %s"
            count_result = fetch_one(count_query, [pref_key])

            if count_result and count_result[0] == 0:
                self.logger.info(
                    f"No preferences found for key '{pref_key}', adding defaults.",
                )
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
                self.save_preferences(pref_key, default_preferences)
            else:
                self.logger.debug(f"Preferences key '{pref_key}' already exists.")

        except Exception as e:
            self.logger.error(f"Error adding default preferences: {e}")

    def _create_feedback_tables(self) -> None:
        """Create feedback and preferences tables if they don't exist using PostgreSQL."""
        feedback_table = "feedback"
        prefs_table = "preferences"
        try:
            # Create feedback table
            if not table_exists(feedback_table):
                self.logger.info(f"Creating {feedback_table} table")
                feedback_cols = (
                    "msg_id VARCHAR(255) PRIMARY KEY, "
                    "subject TEXT, "
                    "original_priority INTEGER, "
                    "assigned_priority INTEGER, "
                    "feedback_comments TEXT, "
                    "suggested_priority INTEGER, "
                    "add_to_topics TEXT[], "
                    "add_to_source VARCHAR(255), "
                    "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                )
                create_feedback = f"CREATE TABLE {feedback_table} ({feedback_cols})"
                execute_query(create_feedback)
                # Add index
                index_feedback = f"CREATE INDEX IF NOT EXISTS feedback_timestamp_idx ON {feedback_table}(timestamp);"
                execute_query(index_feedback)
                self.logger.info(
                    f"Successfully created {feedback_table} table and index.",
                )
            else:
                self.logger.debug(f"Table {feedback_table} already exists.")

            # Create preferences table
            if not table_exists(prefs_table):
                self.logger.info(f"Creating {prefs_table} table")
                prefs_cols = "key VARCHAR(255) PRIMARY KEY, config JSONB"
                create_prefs = f"CREATE TABLE {prefs_table} ({prefs_cols})"
                execute_query(create_prefs)
                self.logger.info(f"Successfully created {prefs_table} table.")
            else:
                self.logger.debug(f"Table {prefs_table} already exists.")

        except Exception as e:
            self.logger.error(f"Error creating feedback/preferences tables: {e}")
            raise

    def load_feedback(self) -> list[dict]:
        """Load feedback entries from database using PostgreSQL utilities."""
        query = "SELECT * FROM feedback ORDER BY timestamp DESC"
        colnames_query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'feedback' ORDER BY ordinal_position;"
        try:
            results = fetch_all(query)
            colnames_result = fetch_all(colnames_query)
            if not colnames_result:
                self.logger.error("Could not fetch column names for feedback table.")
                return []
            colnames = [row[0] for row in colnames_result]
            return [dict(zip(colnames, row, strict=False)) for row in results]
        except Exception as e:
            self.logger.error(f"Error loading feedback: {e}")
            return []

    def load_preferences(self, key: str = "email_preferences") -> dict:
        """Load preferences from database using PostgreSQL utilities."""
        query = "SELECT config FROM preferences WHERE key = %s"
        try:
            result = fetch_one(query, [key])
            if result and result[0]:
                # Result[0] should be a dict if using JSONB/JSON and psycopg2 auto-decoding
                return result[0]
            self.logger.info(
                f"No preferences found for key '{key}'. Returning default.",
            )
            return {"override_rules": []}
        except Exception as e:
            self.logger.error(f"Error loading preferences for key '{key}': {e}")
            return {"override_rules": []}

    def save_feedback(self, feedback_data: list[dict]) -> None:
        """Save feedback entries to database using PostgreSQL UPSERT."""
        # Define the UPSERT query once
        # Make sure column names match the _create_feedback_tables definition
        upsert_query = """
        INSERT INTO feedback (
            msg_id, subject, original_priority, assigned_priority, feedback_comments,
            suggested_priority, add_to_topics, add_to_source, timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (msg_id) DO UPDATE SET
            subject = EXCLUDED.subject,
            original_priority = EXCLUDED.original_priority,
            assigned_priority = EXCLUDED.assigned_priority,
            feedback_comments = EXCLUDED.feedback_comments,
            suggested_priority = EXCLUDED.suggested_priority,
            add_to_topics = EXCLUDED.add_to_topics,
            add_to_source = EXCLUDED.add_to_source,
            timestamp = EXCLUDED.timestamp
        """

        saved_count = 0
        error_count = 0
        for item in feedback_data:
            try:
                params = [
                    item["msg_id"],
                    item.get("subject", ""),
                    item.get("original_priority", None),
                    item.get("assigned_priority", None),
                    item.get("feedback_comments", ""),
                    item.get("suggested_priority", None),
                    item.get("add_to_topics", None),
                    item.get("add_to_source", None),
                    datetime.datetime.fromtimestamp(
                        item.get("timestamp", time.time()), tz=datetime.timezone.utc,
                    ),
                ]
                execute_query(upsert_query, params)
                saved_count += 1
            except Exception as e:
                self.logger.error(
                    f"Error saving feedback item {item.get('msg_id')}: {e}",
                )
                error_count += 1
        self.logger.info(
            f"Feedback save complete. Saved: {saved_count}, Errors: {error_count}",
        )

    def save_preferences(
        self, preferences: dict, key: str = "email_preferences",
    ) -> None:
        """Save preferences to database using PostgreSQL utilities."""
        # Use JSONB/JSON - psycopg2 handles Python dict to JSON conversion
        query = """
        INSERT INTO preferences (key, config)
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET
            config = EXCLUDED.config
        """
        try:
            # Ensure preferences is a dict before trying to dump
            if not isinstance(preferences, dict):
                self.logger.error(
                    f"Preferences data is not a dictionary for key '{key}'. Skipping save.",
                )
                return

            # Pass the dictionary directly, psycopg2 handles json conversion for JSON/JSONB columns
            execute_query(query, [key, json.dumps(preferences)])
            self.logger.info(f"Saved preferences for key '{key}'.")
        except Exception as e:
            self.logger.error(f"Error saving preferences for key '{key}': {e}")

    def generate_feedback_json(
        self,
        feedback_text: str,
        msg_id: str,
        subject: str,
        assigned_priority: int,
        llm_client=None,
        deepinfra_api_key: str = None,
    ) -> dict:
        """
        Uses Deepinfra API to structure natural language feedback into JSON.
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
                error_msg = f"API response was not valid JSON: {e!s}\nResponse Text: {response_content[:200]}"
                self.logger.error(f"Error: {error_msg}")
                return {"error": error_msg, "feedback_text": feedback_text}
        except Exception as e:
            self.logger.error(f"Error calling AI API: {e}")
            self.logger.error("Check your DEEPINFRA_API_KEY and internet connection")
            return {}

    def suggest_rule_changes(
        self, feedback_data: list[dict], preferences: dict,
    ) -> list[dict]:
        """
        Analyzes feedback and suggests changes to preferences.

        Args:
        ----
            feedback_data: List of feedback entries.
            preferences: Dictionary of preferences.

        Returns:
        -------
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
        topic_suggestions = {}
        source_suggestions = {}

        for entry in feedback_data:
            if not entry:
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
                            suggested_priority
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
                        suggested_priority
                    )
        # Output the most common discrepancies
        self.logger.info(
            f"\nMost Common Discrepancies: {discrepancy_counts.most_common()}",
        )

        # 3.  Suggest *new* override rules.  This is the most important part.
        for topic, suggestion in topic_suggestions.items():
            if suggestion["count"] >= 3:
                suggested_changes.append(
                    {
                        "type": "add_override_rule",
                        "keyword": topic,
                        "priority": suggestion["suggested_priority"],
                        "reason": f"Suggested based on feedback (topic appeared {suggestion['count']} times with consistent priority suggestion)",
                    },
                )
        for source, suggestion in source_suggestions.items():
            if suggestion["count"] >= 3:
                suggested_changes.append(
                    {
                        "type": "add_override_rule",
                        "keyword": source,
                        "priority": suggestion["suggested_priority"],
                        "reason": f"Suggested based on feedback (source appeared {suggestion['count']} times with consistent priority suggestion)",
                    },
                )

        # 4 Suggest changes to existing weights.
        discrepancy_sum = 0
        valid_discrepancy_count = 0
        for (assigned, suggested), count in discrepancy_counts.items():
            if suggested is not None:
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
                        "adjustment": 0.1,
                        "reason": "Priorities are consistently lower than user feedback suggests.",
                    },
                )
            else:
                suggested_changes.append(
                    {
                        "type": "adjust_weight",
                        "score_name": "automation_score",
                        "adjustment": 0.1,
                        "reason": "Priorities are consistently higher than user feedback suggests.",
                    },
                )
        return suggested_changes

    def update_preferences(self, preferences: dict, changes: list[dict]) -> dict:
        """
        Applies suggested changes to the preferences.

        Args:
        ----
            preferences: Dictionary of preferences.
            changes: List of suggested changes.

        Returns:
        -------
            Updated dictionary of preferences.

        """
        updated_preferences = preferences.copy()

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
                        new_rule,
                    )
                    self.logger.info(f"  Added override rule: {new_rule}")
                else:
                    self.logger.info("Override rule already exists")
            elif change["type"] == "adjust_weight":
                self.logger.info(
                    "Weight adjustment is only a suggestion, not automatically applied. Manual adjustment recommended",
                )
        return updated_preferences

    def _get_opportunities(self) -> list[tuple]:
        """Get emails that need feedback from PostgreSQL."""
        # Assumes email_analyses table exists in the same database
        query = """
        SELECT ea.msg_id, ea.thread_id, ea.subject, ea.from_address, ea.priority, ea.snippet
        FROM email_analyses ea
        LEFT JOIN feedback fb ON ea.msg_id = fb.msg_id
        WHERE fb.msg_id IS NULL
        ORDER BY ea.from_address, ea.subject
        LIMIT 100
        """
        try:
            results = fetch_all(query)
            if not results:
                self.logger.info(
                    "No feedback opportunities found in email_analyses table.",
                )
                return []

            self.logger.info(
                f"Found {len(results)} potential emails for feedback from {len({r[3] for r in results})} senders.",
            )
            return results

        except Exception as e:
            # Check if it's because the table doesn't exist
            if 'relation "email_analyses" does not exist' in str(e).lower():
                self.logger.warning(
                    "'email_analyses' table not found. Cannot fetch feedback opportunities.",
                )
                self.logger.info(
                    "Run the email classifier first or ensure the table exists.",
                )
                return []
            self.logger.error(f"Error getting feedback opportunities: {e}")
            return []

    def _process_interactive_feedback(self, opportunities: list[tuple]) -> list[dict]:
        """Process email feedback interactively."""
        if not opportunities:
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
            priority = email[4] if len(email) > 4 else 3
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
                },
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
                                },
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
                                    },
                                )
                                self.logger.info(f"  Tagged with: {topics}")
                            break

                        # Check for rule
                        if feedback.lower() in ("r", "rule"):
                            rule_type = input(
                                "  Rule type (topic/sender/block): ",
                            ).strip()
                            if rule_type.lower() in ("topic", "sender", "block"):
                                rule_value = input(
                                    f"  {rule_type.capitalize()} value: ",
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
                                        },
                                    )
                                    self.logger.info(
                                        f"  Created {rule_type} rule for: {rule_value}",
                                    )
                            break

                        # Check for ingest
                        if feedback.lower() in ("i", "ingest"):
                            ingest_type = input(
                                "  Ingest type (form/contact/task): ",
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
                                    },
                                )
                                self.logger.info(
                                    f"  Marked for ingestion as: {ingest_type}",
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
                                },
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
        """
        Execute the feedback processor.

        This implementation satisfies the abstract method requirement from BaseScript.
        Delegates to the run method for actual implementation.
        """
        try:
            self.logger.info(f"Starting execution of {self.name}")
            self.run()
            self.logger.info("Successfully completed feedback processing")
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
                    "No emails found for feedback. Please run the email classifier first.",
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
                                f"Error detaching classifier database: {e}",
                            )

                    # Close connection
                    conn.close()
                    self.logger.debug("Closed database connection")
                except Exception as e:
                    self.logger.debug(f"Error closing database connection: {e}")

    def _maybe_migrate_json_to_db(
        self, conn: DatabaseConnection, existing_feedback: list[dict], preferences: dict,
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
                            f"Migrating feedback data from {feedback_file}",
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
                            f"Migrating preferences data from {prefs_file}",
                        )
                        self.save_preferences(conn, prefs_data)
            except Exception as e:
                self.logger.warning(f"Error migrating preferences data: {e}")


if __name__ == "__main__":
    FeedbackProcessor().execute()
