#!/usr/bin/env python3
"""Gmail synchronization module for integrating Gmail with DuckDB/MotherDuck."""

import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

import duckdb
from dotenv import load_dotenv

# Import directly from dewey module


class GmailSync:
    """Gmail synchronization handler with MotherDuck integration."""

    def __init__(self, gmail_client, db_path: str = "md:dewey"):
        self.gmail_client = gmail_client
        # Set up MotherDuck connection
        load_dotenv()  # Load environment variables from .env file
        self.db_path = db_path
        self.motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
        if self.motherduck_token:
            os.environ["motherduck_token"] = self.motherduck_token

        self.logger = logging.getLogger("gmail_sync")
        self.is_motherduck = self.db_path.startswith("md:")

        # Connection cache to avoid reconnecting constantly
        self._connection = None

        if self.is_motherduck:
            self.logger.info(
                f"🔌 Initializing Gmail sync with MotherDuck database: {self.db_path}"
            )
        else:
            self.logger.info(
                f"💾 Initializing Gmail sync with local database: {self.db_path}"
            )

        self._init_db()

        # Random emoji set for message processing
        self.email_emojis = ["📧", "📨", "📩", "📤", "📥", "💌", "🗨️", "💬", "📝", "🔤"]

    def _get_connection(self):
        """Get a connection to the database, creating it if needed."""
        if self._connection is None:
            try:
                if self.is_motherduck and not self.motherduck_token:
                    self.logger.warning(
                        "⚠️ No MotherDuck token found in environment variables!"
                    )

                # Create a fresh connection
                if self.is_motherduck:
                    # For MotherDuck, use the token from environment
                    config = {"motherduck_token": self.motherduck_token}
                    self.logger.info(f"🔌 Connecting to MotherDuck at {self.db_path}")
                    self._connection = duckdb.connect(self.db_path, config=config)
                else:
                    # For local DB, just connect normally
                    self.logger.info(f"💾 Connecting to local DB at {self.db_path}")
                    self._connection = duckdb.connect(self.db_path)

                # Test the connection with a simple query
                self._connection.execute("SELECT 1").fetchone()
                self.logger.info("✅ Database connection established successfully")

            except Exception as e:
                self.logger.error(f"❌ Database connection error: {e}")
                # Clean up if connection failed
                if self._connection:
                    try:
                        self._connection.close()
                    except:
                        pass
                    self._connection = None
                raise

        return self._connection

    def close_connection(self):
        """Explicitly close the database connection."""
        if self._connection:
            try:
                self._connection.close()
                self.logger.info("🔌 Database connection closed")
            except Exception as e:
                self.logger.warning(f"⚠️ Error closing database connection: {e}")
            finally:
                self._connection = None

    def _init_db(self):
        """Initialize database tables."""
        if self.is_motherduck:
            self.logger.info(
                f"🏗️ Initializing tables in MotherDuck database: {self.db_path}"
            )
        else:
            self.logger.info(f"🏗️ Initializing tables in local database: {self.db_path}")

        try:
            conn = self._get_connection()

            self.logger.info("Creating/verifying raw_emails table...")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_emails (
                    message_id VARCHAR PRIMARY KEY,
                    thread_id VARCHAR,
                    internal_date TIMESTAMP,
                    labels VARCHAR[],
                    subject VARCHAR,
                    sender VARCHAR,
                    recipient VARCHAR,
                    body VARCHAR,
                    headers JSON,
                    attachments VARCHAR[],
                    history_id VARCHAR,
                    raw_data VARCHAR,
                    snippet VARCHAR
                )
            """)
            self.logger.info("📋 Created or verified raw_emails table")

            self.logger.info("Creating/verifying sync_history table...")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY,
                    last_history_id VARCHAR,
                    last_sync TIMESTAMP
                )
            """)
            self.logger.info("📋 Created or verified sync_history table")

            # Verify tables exist and check current state
            self.logger.info("Checking table state...")
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            if "raw_emails" not in table_names or "sync_history" not in table_names:
                self.logger.warning("⚠️ Tables were not created properly!")
            else:
                # Check email count
                try:
                    count = conn.execute("SELECT COUNT(*) FROM raw_emails").fetchone()[
                        0
                    ]
                    self.logger.info(
                        f"✅ Database initialized successfully. Current raw email count: {count}"
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not count emails: {e}")

                # Check sync history
                try:
                    history_count = conn.execute(
                        "SELECT COUNT(*) FROM sync_history"
                    ).fetchone()[0]
                    last_sync = conn.execute("""
                        SELECT last_sync, last_history_id
                        FROM sync_history
                        ORDER BY last_sync DESC
                        LIMIT 1
                    """).fetchone()

                    self.logger.info(f"Sync history entries: {history_count}")
                    if last_sync:
                        self.logger.info(
                            f"Last sync: {last_sync[0]}, Last history ID: {last_sync[1]}"
                        )
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not check sync history: {e}")

        except Exception as e:
            self.logger.error(f"❌ Error initializing database: {e}")
            raise

    def execute(self):
        """Implement abstract method required by parent class."""
        return self.run()

    def run(
        self,
        initial: bool = False,
        query: str | None = None,
        max_results: int = 10000,
    ):
        """Synchronize data with increased default max_results."""
        try:
            if initial:
                self.logger.info(
                    f"🚀 Starting initial sync with max {max_results} messages to {self.db_path}"
                )
                self._process_initial_sync(query, max_results)
            else:
                self.logger.info(f"🔄 Starting incremental sync to {self.db_path}")
                # Check if we have any history to work with
                conn = self._get_connection()
                last_history = conn.execute("""
                    SELECT last_history_id FROM sync_history
                    ORDER BY last_sync DESC LIMIT 1
                """).fetchone()

                if not last_history:
                    self.logger.warning(
                        "⚠️ No sync history found - falling back to initial sync"
                    )
                    self._process_initial_sync(query, max_results)
                else:
                    self.logger.info(f"Found last history ID: {last_history[0]}")
                    self._process_incremental_sync()

            self._update_sync_history()

            # Show count of emails in database
            conn = self._get_connection()
            count = conn.execute("SELECT COUNT(*) FROM raw_emails").fetchone()[0]
            self.logger.info(
                f"✅ Sync completed successfully! Total raw emails in database: {count}"
            )

            # Close connection after sync is complete to avoid hanging connections
            self.close_connection()

            return True

        except Exception as e:
            self.logger.error(f"❌ Sync failed: {e}", exc_info=True)
            # Ensure connection is closed even on error
            self.close_connection()
            raise

    def _process_initial_sync(self, query: str | None, max_results: int):
        """Handle initial full synchronization with larger batch size."""
        page_token = None
        processed = 0
        batch_size = 1000  # Increased batch size for more data

        while True:
            response = self.gmail_client.fetch_emails(
                query=query,
                max_results=min(batch_size, max_results - processed),
                page_token=page_token,
            )

            if not response or "messages" not in response:
                self.logger.info("📭 No messages found or end of results")
                break

            message_count = len(response["messages"])
            self.logger.info(f"📦 Processing batch of {message_count} messages")
            self._process_message_batch(response["messages"])

            processed += message_count
            self.logger.info(
                f"📊 Progress: {processed}/{max_results} messages ({int(processed / max_results * 100)}%)"
            )

            if "nextPageToken" in response and processed < max_results:
                page_token = response["nextPageToken"]
                self.logger.info(f"📃 Fetching next page, processed {processed} so far")
            else:
                self.logger.info(f"🎉 Completed processing {processed} messages")
                break

    def _process_incremental_sync(self):
        """Handle incremental updates using history ID."""
        conn = self._get_connection()
        result = conn.execute(
            "SELECT last_history_id FROM sync_history ORDER BY last_sync DESC LIMIT 1"
        ).fetchone()

        history_id = result[0] if result else None
        if not history_id:
            self.logger.warning(
                "⚠️ No previous history ID found, performing initial sync"
            )
            self._process_initial_sync(None, 10000)
            return

        self.logger.info(f"🕒 Starting incremental sync from history ID: {history_id}")
        history_response = self.gmail_client.get_history(history_id)

        if not history_response:
            self.logger.warning(
                "⚠️ No history available or history ID expired, performing full sync"
            )
            self._process_initial_sync(None, 10000)
            return

        if "history" not in history_response:
            self.logger.info("✅ No changes since last sync")
            return

        processed_ids = set()  # Track which message IDs we've processed

        for history in history_response["history"]:
            # Process deletions first to avoid trying to fetch already-deleted messages
            for deletion in history.get("messagesDeleted", []):
                msg_id = deletion["message"]["id"]
                if msg_id not in processed_ids:
                    self.logger.info(f"➖ Deleting message: {msg_id}")
                    conn.execute(
                        "DELETE FROM raw_emails WHERE message_id = ?", [msg_id]
                    )
                    processed_ids.add(msg_id)

            # Then process additions
            for addition in history.get("messagesAdded", []):
                msg_id = addition["message"]["id"]
                if msg_id in processed_ids:
                    continue  # Skip if we've already processed this ID

                self.logger.info(f"➕ Processing added message: {msg_id}")
                try:
                    full_msg = self.gmail_client.get_message(msg_id, format="full")
                    if full_msg:
                        parsed = self._parse_message(full_msg)
                        self._store_message(parsed)
                        processed_ids.add(msg_id)
                except Exception as e:
                    if "404" in str(e):
                        # Message was probably deleted or moved before we could fetch it
                        self.logger.debug(
                            f"Message {msg_id} no longer available (probably deleted)"
                        )
                        continue
                    else:
                        self.logger.error(f"Error processing message {msg_id}: {e}")

            # Handle label changes if needed
            for label_added in history.get("labelsAdded", []):
                msg_id = label_added["message"]["id"]
                if msg_id not in processed_ids:
                    try:
                        full_msg = self.gmail_client.get_message(msg_id, format="full")
                        if full_msg:
                            parsed = self._parse_message(full_msg)
                            self._store_message(parsed)
                            processed_ids.add(msg_id)
                    except Exception as e:
                        if "404" in str(e):
                            self.logger.debug(f"Message {msg_id} no longer available")
                            continue
                        else:
                            self.logger.error(
                                f"Error processing label change for {msg_id}: {e}"
                            )

        total_processed = len(processed_ids)
        self.logger.info(
            f"✅ Incremental sync completed. Processed {total_processed} messages"
        )

    def _process_message_batch(self, messages: list[dict]):
        """Process a batch of messages with retry logic, getting complete data."""
        success_count = 0
        for idx, msg in enumerate(messages):
            emoji = random.choice(self.email_emojis)
            for attempt in range(3):
                try:
                    msg_id = msg["id"]
                    # Only log every 10th message to reduce noise
                    if idx % 10 == 0:
                        self.logger.info(
                            f"{emoji} Processing message {idx + 1}/{len(messages)}: {msg_id[:8]}..."
                        )

                    full_msg = self.gmail_client.get_message(msg_id, format="full")
                    if full_msg:
                        parsed = self._parse_message(full_msg)
                        self._store_message(parsed)
                        success_count += 1
                    else:
                        self.logger.warning(f"⚠️ Could not retrieve message {msg_id}")
                    break
                except Exception as e:
                    if attempt == 2:
                        self.logger.error(f"❌ Failed to process message {msg_id}: {e}")
                    else:
                        backoff_time = 2**attempt
                        self.logger.warning(
                            f"⏱️ Retry {attempt + 1} for message {msg_id}: {e}. Waiting {backoff_time}s..."
                        )
                        time.sleep(backoff_time)  # Exponential backoff

        self.logger.info(
            f"✅ Successfully processed {success_count}/{len(messages)} messages in batch"
        )

    def _parse_message(self, message: dict) -> dict:
        """Parse raw Gmail message into structured format with complete data."""
        payload = message.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        # Extract message parts recursively
        body = self._extract_body_parts(payload)

        return {
            "message_id": message["id"],
            "thread_id": message.get("threadId"),
            "internal_date": datetime.fromtimestamp(
                int(message.get("internalDate", 0)) / 1000
            ),
            "labels": message.get("labelIds", []),
            "subject": headers.get("Subject"),
            "sender": headers.get("From"),
            "recipient": headers.get("To"),
            "body": body,
            "headers": headers,
            "attachments": self._extract_attachments(payload),
            "history_id": message.get("historyId"),
            "raw_data": message.get("raw", ""),
            "snippet": message.get("snippet", ""),
        }

    def _extract_body_parts(self, payload: dict) -> str:
        """Extract message body from all relevant parts."""
        if not payload:
            return ""

        body = ""
        # Check for body in the main payload
        if "body" in payload and "data" in payload["body"]:
            body += self.gmail_client.decode_message_body(payload["body"])

        # Check for parts
        for part in payload.get("parts", []):
            if part.get("mimeType", "").startswith("text/"):
                if "body" in part and "data" in part["body"]:
                    body += self.gmail_client.decode_message_body(part["body"])
            elif "parts" in part:
                # Recursive extraction for multipart messages
                body += self._extract_body_parts(part)

        return body

    def _extract_attachments(self, payload: dict) -> list[str]:
        """Extract attachment filenames from message."""
        attachments = []

        if not payload:
            return attachments

        # Check for inline attachments
        if payload.get("filename") and payload.get("mimeType", "").startswith(
            "application/"
        ):
            attachments.append(payload["filename"])

        # Check parts recursively
        for part in payload.get("parts", []):
            if part.get("filename") and "body" in part:
                attachments.append(part["filename"])
            elif "parts" in part:
                attachments.extend(self._extract_attachments(part))

        return attachments

    def _store_message(self, message: dict):
        """Upsert message into database using raw_emails table."""
        conn = self._get_connection()

        # Convert headers to JSON string
        headers_json = json.dumps(message["headers"])

        # Use the new raw_emails table
        conn.execute(
            """
            INSERT OR REPLACE INTO raw_emails
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                message["message_id"],
                message["thread_id"],
                message["internal_date"],
                message["labels"],  # Arrays should work with DuckDB
                message["subject"],
                message["sender"],
                message["recipient"],
                message["body"],
                headers_json,  # JSON string instead of map
                message["attachments"],  # Arrays should work with DuckDB
                message["history_id"],
                message.get("raw_data", ""),
                message.get("snippet", ""),
            ],
        )

    def _update_sync_history(self):
        """Update sync history tracking."""
        latest_history_id = self._get_latest_history_id()
        if latest_history_id:
            conn = self._get_connection()
            # Handle ID generation by omitting it from both field list and values
            max_id_result = conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM sync_history"
            ).fetchone()
            next_id = (max_id_result[0] or 0) + 1

            conn.execute(
                """
                INSERT INTO sync_history (id, last_history_id, last_sync)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                [next_id, latest_history_id],
            )
            self.logger.info(f"📝 Updated sync history with ID: {latest_history_id}")

    def _get_latest_history_id(self) -> str | None:
        """Get most recent history ID from messages."""
        conn = self._get_connection()
        result = conn.execute(
            "SELECT history_id FROM raw_emails ORDER BY internal_date DESC LIMIT 1"
        ).fetchone()
        return result[0] if result else None

    def __del__(self):
        """Ensure connection is closed when object is destroyed."""
        self.close_connection()
