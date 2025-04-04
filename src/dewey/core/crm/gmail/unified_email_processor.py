#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from src.dewey.core.base_script import BaseScript
from src.dewey.core.db.connection import db_manager
from src.dewey.core.crm.gmail.gmail_utils import OAuthGmailClient


class UnifiedEmailProcessor(BaseScript):
    """
    Unified processor that handles Gmail sync, enrichment, and prioritization.
    Includes contact extraction and email signature parsing.
    """

    def __init__(self):
        """Initialize the unified processor with proper config section."""
        super().__init__(
            config_section="crm.gmail",  # Use proper config section from dewey.yaml
            requires_db=True,  # Indicate we need database access
        )

        # Load environment variables
        load_dotenv()

        # Initialize components
        self.gmail_sync = None
        self._interrupted = False

        # Configuration
        self.sync_interval = self.get_config_value(
            "sync_interval_seconds", 300,
        )  # 5 minutes default
        self.max_results_per_sync = self.get_config_value("max_results_per_sync", 1000)

        # Email signature patterns from config
        self.signature_patterns = self.get_config_value(
            "regex_patterns.contact_info",
            {
                "phone": r"(?:Phone|Tel|Mobile|Cell)?\s*[:.]?\s*((?:\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
                "email": r"[\w\.-]+@[\w\.-]+\.\w+",
                "title": r"(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\||,|\n)",
                "company": r"(?:@|at)\s*([A-Z][A-Za-z0-9\s&]+)(?:\s|$|\n)",
                "linkedin": r"linkedin\.com/in/[\w-]+",
                "twitter": r"twitter\.com/[\w-]+",
            },
        )

        # Try to load EmailEnrichment only if it exists
        try:
            from src.dewey.core.crm.enrichment.email_enrichment import EmailEnrichment

            self.enrichment = EmailEnrichment()
        except ImportError:
            self.logger.warning(
                "EmailEnrichment module not found, continuing without it",
            )
            self.enrichment = None

        # Setup database tables once during initialization
        try:
            self._setup_database_tables()
            self.logger.info(
                "Database tables set up successfully during initialization",
            )
        except Exception as e:
            self.logger.error("Error setting up database tables: %s", e, exc_info=True)
            # We'll continue execution and try again later if needed

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers to catch interruptions."""
        try:
            import signal

            # Register signal handlers
            signal.signal(signal.SIGINT, self.__signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, self.__signal_handler)  # Termination signal
            self.logger.debug("Signal handlers registered")
        except (ImportError, AttributeError) as e:
            self.logger.warning("Could not set up signal handlers: %s", e)

    def execute(self) -> None:
        """Main execution method following BaseScript convention."""
        try:
            self.logger.info("🔄 Starting email processing cycle")

            # Setup Gmail client if not already initialized
            if not self.gmail_sync:
                self.setup_gmail_client()

            # Setup database tables early to prevent errors later
            try:
                self._setup_database_tables()
            except Exception as e:
                self.logger.error(
                    "❌ Error setting up database tables: %s", e, exc_info=True,
                )
                # Continue execution - we'll try to work with existing tables

            # 1. First sync any new emails from Gmail
            try:
                self.sync_new_emails()
            except Exception as e:
                self.logger.error("❌ Error syncing new emails: %s", e, exc_info=True)
                # Continue with processing existing emails

            # 2. Then process any unprocessed emails in the database
            try:
                self.process_unprocessed_emails()
            except Exception as e:
                self.logger.error(
                    "❌ Error processing unprocessed emails: %s", e, exc_info=True,
                )

            self.logger.info("✅ Email processing cycle completed successfully")

        except KeyboardInterrupt:
            self.logger.info("⏹️ Process interrupted by user. Shutting down gracefully.")
            # Clean up resources
            if self.gmail_sync:
                try:
                    self.gmail_sync.close_connection()
                except:
                    pass
        except Exception as e:
            self.logger.error("❌ Error in processing cycle: %s", e, exc_info=True)
            raise

    def setup_gmail_client(self):
        """Setup the Gmail client to sync emails."""
        self.logger.info("🔄 Setting up Gmail client with MotherDuck database")

        # Initialize OAuthGmailClient for authentication
        try:
            # Get credentials path from config or use default
            credentials_dir = self.get_config_value(
                "paths.credentials_dir", "config/credentials",
            )
            credentials_path = self.get_path(
                os.path.join(credentials_dir, "credentials.json"),
            )
            token_path = self.get_path(
                os.path.join(credentials_dir, "gmail_token.json"),
            )

            self.logger.info(
                "Initializing Gmail client with credentials from %s", credentials_path,
            )

            # Initialize the Gmail OAuth client
            gmail_client = OAuthGmailClient(
                credentials_file=str(credentials_path), token_file=str(token_path),
            )

            if not gmail_client.authenticate():
                raise Exception("Failed to authenticate with Gmail API")

            # Get MotherDuck database name from config
            motherduck_db = self.get_config_value("database.motherduck_db", "md:dewey")
            self.logger.info("📊 Using MotherDuck database: %s", motherduck_db)

            # Initialize GmailSync with the authenticated client and MotherDuck path
            from src.dewey.core.crm.gmail.gmail_sync import GmailSync
            gmail_sync = GmailSync(
                credentials_file=str(credentials_path), db_path=motherduck_db, token_file=str(token_path)
            )

            self.gmail_sync = gmail_sync

            self.logger.info("✅ Gmail client initialized successfully with MotherDuck")
        except Exception as e:
            self.logger.error("❌ Error initializing Gmail client: %s", e)
            raise

    def sync_new_emails(self):
        """Sync new emails from Gmail."""
        self.logger.info("📧 Running Gmail sync")

        # This will fetch new emails and store them in the database
        self.gmail_sync.run(initial=False, max_results=self.max_results_per_sync)

    def process_unprocessed_emails(self):
        """Process all unprocessed emails in the database."""
        self.logger.info("🔍 Finding unprocessed emails")

        # Import here to allow connection refreshes
        from dewey.core.db import db_manager

        # Get batch size from config or use default
        batch_size = self.get_config_value(
            "batch_size", 100,
        )  # Larger batch size for faster processing
        max_emails = self.get_config_value("max_emails", 1000)

        # Add a small delay between write operations to reduce concurrent writes
        write_delay = self.get_config_value(
            "write_delay", 0.1,
        )  # 100ms delay between writes

        # Query once to get total count
        try:
            total_count_query = """
                SELECT COUNT(*)
                FROM raw_emails r
                LEFT JOIN email_analyses e ON r.message_id = e.msg_id
                WHERE e.msg_id IS NULL
                   OR e.status = 'pending'
                LIMIT ?
            """
            total_count_result = db_manager.execute_query(
                total_count_query, [max_emails],
            )
            total_count = total_count_result[0][0] if total_count_result else 0

            if total_count == 0:
                self.logger.info("✅ No unprocessed emails found!")
                return

            self.logger.info(
                "📨 Found %s emails to process (limiting to %s)",
                total_count,
                max_emails,
            )
        except Exception as e:
            self.logger.error("❌ Error counting unprocessed emails: %s", e)
            # Default to proceeding without knowing the count
            total_count = None

        # Process in batches to avoid memory issues and allow interruption
        processed_count = 0
        error_count = 0
        start_time = time.time()

        # Use a list to track recent processing rates for better estimation
        recent_rates = []
        max_rate_samples = 5  # Number of recent batches to average

        # Track when we last released DB connections
        last_db_release = time.time()
        db_release_interval = 60  # Release DB connections every 60 seconds

        while processed_count < max_emails:
            # Release database connections periodically
            current_time = time.time()
            if current_time - last_db_release > db_release_interval:
                self._maybe_release_db_connections()
                # Re-import after connection refresh
                from dewey.core.db import db_manager

                last_db_release = current_time

            try:
                # Get a batch of emails to process
                query = """
                    SELECT message_id
                    FROM raw_emails r
                    LEFT JOIN email_analyses e ON r.message_id = e.msg_id
                    WHERE e.msg_id IS NULL
                       OR e.status = 'pending'
                    ORDER BY r.internal_date DESC
                    LIMIT ?
                """
                new_emails = db_manager.execute_query(query, [batch_size])

                if not new_emails:
                    break  # No more emails to process

                batch_count = len(new_emails)
                batch_start_time = time.time()
                self.logger.info("📧 Processing batch of %s emails", batch_count)

                # Process the batch
                batch_success = 0
                batch_error = 0

                # Process each email in the batch
                for i, (email_id,) in enumerate(new_emails):
                    try:
                        # Add a small delay between emails to reduce concurrent write operations
                        # Skip delay for the first email in the batch
                        if i > 0 and write_delay > 0:
                            time.sleep(write_delay)

                        if self._process_single_email(email_id):
                            batch_success += 1
                        else:
                            batch_error += 1

                        # Release DB connections every 25 emails to prevent long-term locking
                        if (i + 1) % 25 == 0:
                            self._maybe_release_db_connections()
                            # Re-import after connection refresh
                            from dewey.core.db import db_manager

                    except Exception as e:
                        self.logger.error(
                            "❌ Error processing email %s: %s",
                            email_id,
                            str(e),
                            exc_info=True,
                        )
                        batch_error += 1

                # Update counts
                processed_count += batch_count
                error_count += batch_error

                # Calculate and show progress
                batch_time = time.time() - batch_start_time
                rate = batch_count / batch_time if batch_time > 0 else 0
                recent_rates.append(rate)
                if len(recent_rates) > max_rate_samples:
                    recent_rates.pop(0)  # Keep only the most recent samples

                avg_rate = sum(recent_rates) / len(recent_rates) if recent_rates else 0
                elapsed_time = time.time() - start_time

                # Estimate remaining time
                remaining = total_count - processed_count if total_count else "unknown"
                remaining_time = (
                    (total_count - processed_count) / avg_rate
                    if total_count and avg_rate > 0
                    else "unknown"
                )

                if isinstance(remaining_time, str):
                    eta_str = "unknown"
                else:
                    eta_str = f"{remaining_time:.1f} seconds"

                self.logger.info(
                    "✓ Processed %s/%s emails (%s/%s success in %.1fs, rate: %.1f/s, avg: %.1f/s, ETA: %s)",
                    processed_count,
                    total_count or "unknown",
                    batch_success,
                    batch_count,
                    batch_time,
                    rate,
                    avg_rate,
                    eta_str,
                )

                # Adaptive delay - if we're getting write conflicts, slow down
                # Check if we have logs from the last processing indicating write conflicts
                write_conflicts = False
                try:
                    # Simple check - better implementation would be to analyze logs
                    if (
                        hasattr(self, "had_write_conflicts")
                        and self.had_write_conflicts
                    ):
                        write_conflicts = True
                        # Reset the flag
                        self.had_write_conflicts = False
                except Exception:
                    pass

                # If we detected write conflicts, increase the delay
                if write_conflicts and write_delay < 0.5:  # Cap at 500ms
                    old_delay = write_delay
                    write_delay = min(
                        write_delay * 1.5, 0.5,
                    )  # Increase by 50% up to 500ms
                    self.logger.info(
                        f"Write conflicts detected, increasing delay from {old_delay:.2f}s to {write_delay:.2f}s",
                    )

            except Exception as e:
                self.logger.error(f"❌ Error processing batch: {e}", exc_info=True)
                error_count += batch_count
                processed_count += batch_count  # Count as processed even if errors

                # Set the conflicts flag
                self.had_write_conflicts = "write-write conflict" in str(e)

        # Done processing
        total_time = time.time() - start_time
        success_count = processed_count - error_count

        self.logger.info(
            "🏁 Processing complete: %s/%s emails processed successfully "
            "in {:.1f} seconds ({:.1f}/s)",
            success_count,
            processed_count,
            total_time,
            processed_count / total_time,
        )

    def _setup_database_tables(self):
        """Ensure we have the necessary database tables and columns."""
        existing_tables = self._get_existing_tables()

        # Create email_analyses table if it doesn't exist
        if "email_analyses" not in existing_tables:
            self.logger.info("🔃 Creating email_analyses table")
            try:
                # Create with the standard schema
                # Use non-conflicting column names for PRIMARY KEY
                db_manager.execute_query(
                    """
                    CREATE TABLE IF NOT EXISTS email_analyses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        msg_id VARCHAR UNIQUE,
                        email_id VARCHAR UNIQUE,
                        thread_id VARCHAR,
                        subject VARCHAR,
                        from_address VARCHAR,
                        analysis_date TIMESTAMP,
                        priority INTEGER,
                        status VARCHAR DEFAULT 'new',
                        metadata JSON,
                        processed BOOLEAN DEFAULT FALSE,
                        priority_score FLOAT,
                        extracted_contacts JSON,
                        processed_timestamp TIMESTAMP
                    )
                """,
                    for_write=True,
                )

                # Create indexes to help lookups
                try:
                    db_manager.execute_query(
                        """
                        CREATE INDEX IF NOT EXISTS idx_email_analyses_msg_id ON email_analyses(msg_id)
                    """,
                    for_write=True,
                    )

                    db_manager.execute_query(
                        """
                        CREATE INDEX IF NOT EXISTS idx_email_analyses_email_id ON email_analyses(email_id)
                    """,
                    for_write=True,
                    )
                except Exception as e:
                    self.logger.warning(
                        "Could not create indexes on email_analyses: %s", e,
                    )

            except Exception as e:
                self.logger.error(f"Failed to create email_analyses table: {e}")
        else:
            # Ensure necessary columns exist in email_analyses table
            self.logger.info("🔍 Checking email_analyses columns")
            try:
                # Get existing columns
                columns_result = db_manager.execute_query(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'email_analyses'
                """,
                )
                existing_columns = (
                    [row[0].lower() for row in columns_result] if columns_result else []
                )

                # Define columns to ensure they exist
                required_columns = {
                    # New columns for the enhanced schema
                    "id": "INTEGER",
                    # Standard schema columns
                    "msg_id": "VARCHAR",
                    "thread_id": "VARCHAR",
                    "subject": "VARCHAR",
                    "from_address": "VARCHAR",
                    "analysis_date": "TIMESTAMP",
                    "priority": "INTEGER",
                    "status": "VARCHAR",
                    "metadata": "JSON",
                    # Alternative schema columns
                    "email_id": "VARCHAR",
                    "processed": "BOOLEAN",
                    "priority_score": "FLOAT",
                    "extracted_contacts": "JSON",
                    "processed_timestamp": "TIMESTAMP",
                }

                # Add missing columns
                for col_name, col_type in required_columns.items():
                    if col_name.lower() not in existing_columns:
                        self.logger.info(
                            f"➕ Adding missing column to email_analyses: {col_name}",
                        )
                        try:
                            default_value = ""
                            if col_type == "BOOLEAN":
                                default_value = "DEFAULT FALSE"
                            elif col_type == "INTEGER" or col_type == "FLOAT":
                                default_value = "DEFAULT 0"
                            elif col_type == "TIMESTAMP":
                                default_value = "DEFAULT CURRENT_TIMESTAMP"

                            db_manager.execute_query(
                                f"""
                                ALTER TABLE email_analyses
                                ADD COLUMN {col_name} {col_type} {default_value}
                            """,
                                for_write=True,
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Could not add column {col_name} to email_analyses: {e}",
                            )

            except Exception as e:
                self.logger.error(
                    "Could not check or update email_analyses columns: %s", e,
                )

    def _get_existing_tables(self) -> list[str]:
        """Get a list of existing tables in the database."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            tables_result = db_manager.execute_query("SHOW TABLES")
            existing_tables = [row[0].lower() for row in tables_result] if tables_result else []
            return existing_tables
        except Exception as e:
            self.logger.error("Could not retrieve existing tables: %s", e)
            return []

    def _get_contact_table_columns(self) -> list[str]:
        """Get a list of columns in the contacts table."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            columns_result = db_manager.execute_query(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'contacts'
            """,
            )
            existing_columns = (
                [row[0].lower() for row in columns_result] if columns_result else []
            )
            return existing_columns
        except Exception as e:
            self.logger.error("Could not retrieve contact table columns: %s", e)
            return []

    def _process_single_email(self, email_id):
        """Process a single email by ID."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Get the raw email data
            query = "SELECT * FROM raw_emails WHERE message_id = ?"
            email_result = db_manager.execute_query(query, [email_id])

            if not email_result:
                self.logger.warning("⚠️ Email %s not found in raw_emails", email_id)
                return False

            # Extract email data
            (
                message_id,
                thread_id,
                internal_date,
                labels,
                subject,
                from_address,
                recipient,
                body,
                headers,
                attachments,
                history_id,
                raw_data,
                snippet,
            ) = email_result[0]

            # Extract contact information from the email
            contact_info = self._extract_contact_info(from_address, email_id)

            # Store the email analysis
            self._store_email_analysis(
                msg_id=message_id,
                thread_id=thread_id,
                subject=subject,
                from_address=from_address,
                contact_info=contact_info,
                email_id=email_id,
                priority_score=0.0,  # Initial score
            )

            # Update timestamp fields
            self._update_timestamp_fields(msg_id=message_id)

            # Update internal date
            self._update_internal_date(msg_id=message_id, internal_date=internal_date)

            # Enrich contact from email
            self._enrich_contact_from_email(email_id=email_id, contact_info=contact_info)

            # Calculate priority score
            self._calculate_priority_score(email_id=email_id)

            return True  # Indicate success

        except Exception as e:
            self.logger.error("❌ Error processing email %s: %s", email_id, str(e))
            return False  # Indicate failure

    def _extract_contact_info(self, from_address, email_id):
        """Extract contact information from email signature."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Get the raw email data
            query = "SELECT body FROM raw_emails WHERE message_id = ?"
            email_result = db_manager.execute_query(query, [email_id])

            if not email_result:
                self.logger.warning("⚠️ Email %s not found in raw_emails", email_id)
                return {}

            body = email_result[0][0]

            # Extract contact information from the email signature
            contact_info = {}
            for field, pattern in self.signature_patterns.items():
                match = None
                try:
                    import re

                    match = re.search(pattern, body, re.MULTILINE)
                except Exception as e:
                    self.logger.warning(
                        "Could not compile regex pattern for %s: %s", field, e,
                    )
                    continue

                if match:
                    contact_info[field] = match.group(1).strip()
                    self.logger.debug(
                        "Extracted %s: %s from email %s", field, contact_info[field], email_id,
                    )

            # Add the from address to the contact info
            contact_info["email"] = from_address

            return contact_info
        except Exception as e:
            self.logger.error("❌ Error extracting contact info: %s", e)
            return {}

    def _get_column_names(self, table_name: str) -> list[str]:
        """Get a list of column names for a given table."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            columns_result = db_manager.execute_query(
                f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """,
            )
            existing_columns = (
                [row[0].lower() for row in columns_result] if columns_result else []
            )
            return existing_columns
        except Exception as e:
            self.logger.error("Could not retrieve column names for %s: %s", table_name, e)
            return []

    def _store_email_analysis(
        self,
        msg_id: str,
        thread_id: str,
        subject: str,
        from_address: str,
        contact_info: dict[str, Any],
        email_id: str,
        priority_score: float,
    ):
        """Store email analysis results in the database."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Convert contact info to JSON string
            contact_info_json = json.dumps(contact_info)

            # Use parameterized query to prevent SQL injection
            query = """
                INSERT OR REPLACE INTO email_analyses (
                    msg_id,
                    thread_id,
                    subject,
                    from_address,
                    analysis_date,
                    priority,
                    status,
                    metadata,
                    email_id,
                    processed,
                    priority_score,
                    extracted_contacts,
                    processed_timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Execute the query with the parameters
            db_manager.execute_query(
                query,
                [
                    msg_id,
                    thread_id,
                    subject,
                    from_address,
                    datetime.utcnow(),
                    0,  # Initial priority
                    "complete",  # Set status to complete
                    "{}",  # Empty metadata
                    email_id,
                    True,  # Set processed to True
                    priority_score,
                    contact_info_json,
                    datetime.utcnow(),
                ],
                for_write=True,
            )

            self.logger.debug("Stored email analysis for %s", msg_id)

        except Exception as e:
            self.logger.error("❌ Error storing email analysis: %s", e)

    def _update_timestamp_fields(
        self,
        msg_id: str,
    ):
        """Update timestamp fields in the email_analyses table."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Update the analysis_date and processed_timestamp fields
            db_manager.execute_query(
                """
                UPDATE email_analyses
                SET analysis_date = ?, processed_timestamp = ?
                WHERE msg_id = ?
            """,
                [datetime.utcnow(), datetime.utcnow(), msg_id],
                for_write=True,
            )
            self.logger.debug("Updated timestamp fields for %s", msg_id)
        except Exception as e:
            self.logger.error("❌ Error updating timestamp fields: %s", e)

    def _update_internal_date(
        self,
        msg_id: str,
        internal_date: datetime,
    ):
        """Update internal date in the email_analyses table."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Update the analysis_date and processed_timestamp fields
            db_manager.execute_query(
                """
                UPDATE email_analyses
                SET internal_date = ?
                WHERE msg_id = ?
            """,
                [internal_date, msg_id],
                for_write=True,
            )
            self.logger.debug("Updated internal_date for %s", msg_id)
        except Exception as e:
            self.logger.error("❌ Error updating internal_date: %s", e)

    def _update_field(self, msg_id, field_name, value):
        """Generic method to update a single field in the email_analyses table."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Update the specified field
            db_manager.execute_query(
                f"""
                UPDATE email_analyses
                SET {field_name} = ?
                WHERE msg_id = ?
            """,
                [value, msg_id],
                for_write=True,
            )
            self.logger.debug(f"Updated {field_name} for {msg_id}")
        except Exception as e:
            self.logger.error(f"❌ Error updating {field_name}: %s", e)

    def _enrich_contact_from_email(self, email_id: str, contact_info: dict[str, Any]):
        """Enrich contact information from email."""
        if not self.enrichment:
            self.logger.debug("Skipping contact enrichment - module not loaded")
            return

        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Get the raw email data
            query = "SELECT from_address FROM raw_emails WHERE message_id = ?"
            email_result = db_manager.execute_query(query, [email_id])

            if not email_result:
                self.logger.warning("⚠️ Email %s not found in raw_emails", email_id)
                return

            from_address = email_result[0][0]

            # Enrich the contact information
            enriched_contact = self.enrichment.enrich_contact(contact_info)

            # Get the contact table columns
            contact_table_columns = self._get_contact_table_columns()

            # Prepare the insert values
            insert_values = []
            insert_columns = []

            # Add the enriched contact information to the insert values
            for column in contact_table_columns:
                if column in enriched_contact:
                    insert_values.append(enriched_contact[column])
                    insert_columns.append(column)
                else:
                    insert_values.append(None)

            # Add the from address to the insert values
            if "email" in contact_table_columns and "email" not in insert_columns:
                insert_values.append(from_address)
                insert_columns.append("email")

            # Create the insert query
            insert_query = f"""
                INSERT OR IGNORE INTO contacts ({', '.join(insert_columns)})
                VALUES ({', '.join(['?' for _ in insert_columns])})
            """

            # Execute the insert query
            db_manager.execute_query(insert_query, insert_values, for_write=True)

            self.logger.debug("Enriched contact information for %s", email_id)

        except Exception as e:
            self.logger.error("❌ Error enriching contact: %s", e)

    def _calculate_priority_score(
        self,
        email_id: str,
    ):
        """Calculate priority score for an email."""
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Get the raw email data
            query = "SELECT body, subject FROM raw_emails WHERE message_id = ?"
            email_result = db_manager.execute_query(query, [email_id])

            if not email_result:
                self.logger.warning("⚠️ Email %s not found in raw_emails", email_id)
                return

            body, subject = email_result[0]

            # Calculate the priority score based on the email body and subject
            priority_score = 0.0
            if "urgent" in body.lower() or "important" in subject.lower():
                priority_score += 0.5
            if "action required" in body.lower() or "action needed" in subject.lower():
                priority_score += 0.3
            if "meeting" in body.lower() or "schedule" in subject.lower():
                priority_score += 0.2

            # Update the priority score in the email_analyses table
            self._update_field(email_id, "priority_score", priority_score)

            self.logger.debug("Calculated priority score for %s: %s", email_id, priority_score)

        except Exception as e:
            self.logger.error("❌ Error calculating priority score: %s", e)

    def _cleanup(self) -> None:
        """Clean up resources."""
        self.logger.info("Cleaning up resources")
        if self.gmail_sync:
            try:
                self.gmail_sync.close_connection()
            except:
                pass

    def __signal_handler(self, sig, frame):
        """Handle signals to allow graceful exit."""
        self.logger.info("Signal received, stopping processing...")
        self._interrupted = True

    def _maybe_release_db_connections(self):
        """Release database connections to prevent long-term locking."""
        self.logger.debug("Releasing database connections")
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            db_manager.close_all_connections()
            self.logger.debug("Database connections released")
        except Exception as e:
            self.logger.error("Could not release database connections: %s", e)


                    )
                    contact_exists = existing and existing[0][0] > 0
                except Exception as e2:
                    self.logger.warning(f"Backup check for contact failed: {e2}")

            if contact_exists:
                # Just update the incrementable fields with minimal SQL to avoid errors
                # Use a more defensive update query with better error handling
                try:
                    db_manager.execute_query(
                        """
                        UPDATE contacts
                        SET last_updated = ?,
                            email_count = COALESCE(email_count, 0) + 1,
                            confidence_score = ?
                        WHERE email = ?
                    """,
                        [
                            now_str,
                            simple_contact["confidence_score"],
                            simple_contact["email"],
                        ],
                        for_write=True,
                    )
                    self.logger.debug(
                        "Updated existing contact: %s", simple_contact["email"],
                    )
                except Exception as e:
                    self.logger.warning("Error updating contact: %s", e)
                    # Try a simpler update as fallback
                    try:
                        db_manager.execute_query(
                            """
                            UPDATE contacts
                            SET last_updated = ?
                            WHERE email = ?
                        """,
                            [now_str, simple_contact["email"]],
                            for_write=True,
                        )
                    except Exception as e2:
                        self.logger.error(
                            "Both update attempts failed for contact %s: %s",
                            simple_contact["email"],
                            e2,
                        )
            else:
                # Insert new contact with minimal required fields
                try:
                    # Use a more defensive query with fewer required fields
                    insert_query = """
                        INSERT INTO contacts (
                            email, is_client, confidence_score, created_at, last_updated
                        ) VALUES (
                            ?, ?, ?, ?, ?
                        )
                    """
                    db_manager.execute_query(
                        insert_query,
                        [
                            simple_contact["email"],
                            simple_contact.get("is_client", False),
                            simple_contact.get("confidence_score", 0.0),
                            now_str,
                            now_str,
                        ],
                        for_write=True,
                    )
                    self.logger.debug(
                        f"Inserted new contact: {simple_contact['email']}",
                    )

                    # Try to update with additional fields if they exist
                    if simple_contact.get("first_name") or simple_contact.get(
                        "last_name",
                    ):
                        try:
                            update_query = """
                                UPDATE contacts
                                SET first_name = ?,
                                    last_name = ?,
                                    full_name = ?,
                                    company = ?,
                                    job_title = ?
                                WHERE email = ?
                            """
                            db_manager.execute_query(
                                update_query,
                                [
                                    simple_contact.get("first_name"),
                                    simple_contact.get("last_name"),
                                    simple_contact.get("full_name"),
                                    simple_contact.get("company"),
                                    simple_contact.get("job_title"),
                                    simple_contact["email"],
                                ],
                                for_write=True,
                            )
                        except Exception as e:
                            self.logger.warning(
                                "Could not update additional contact info: %s", e,
                            )
                except Exception as e:
                    self.logger.warning("Error inserting contact: %s", e)
                    # Try an absolutely minimal insert as last resort
                    try:
                        # Use plain INSERT instead of INSERT OR IGNORE
                        # First check if it exists again to be extra safe
                        exists_check = db_manager.execute_query(
                            """
                            SELECT COUNT(*) FROM contacts WHERE email = ?
                        """,
                            [simple_contact["email"]],
                        )

                        if not exists_check or exists_check[0][0] == 0:
                            db_manager.execute_query(
                                """
                                INSERT INTO contacts (
                                    email, created_at, last_updated
                                ) VALUES (
                                    ?, ?, ?
                                )
                            """,
                                [simple_contact["email"], now_str, now_str],
                                for_write=True,
                            )
                    except Exception as e2:
                        self.logger.error(
                            "All insert attempts failed for %s: %s",
                            simple_contact["email"],
                            e2,
                        )
        except Exception as e:
            self.logger.error(
                "Error enriching contact from email: %s", e, exc_info=True,
            )

    def _calculate_priority_score(
        self, contact_info: dict[str, Any], body: str,
    ) -> float:
        """Calculate priority score based on contact and email content."""
        # Get priority weights from config
        priority_weights = self.get_config_value(
            "crm.enrichment.priority_weights",
            {
                "is_client": 0.5,
                "title_match": 0.2,
                "company_match": 0.1,
                "urgent_keywords": 0.2,
                "opportunity_keywords": 0.2,
            },
        )

        score = 0.0

        # Client status is highest priority factor
        if contact_info.get("is_client"):
            score += priority_weights.get("is_client", 0.5)

        # Contact-based scoring
        if contact_info.get("company"):
            score += priority_weights.get("company_match", 0.1)

        if contact_info.get("title"):
            if any(
                word in contact_info["title"].lower()
                for word in ["ceo", "founder", "director", "vp", "president"]
            ):
                score += priority_weights.get("title_match", 0.2)
            else:
                score += priority_weights.get("title_match", 0.2) / 2

        # Content-based scoring
        urgent_keywords = ["urgent", "asap", "emergency", "deadline", "important"]
        opportunity_keywords = [
            "opportunity",
            "proposal",
            "contract",
            "deal",
            "partnership",
        ]

        if any(keyword in body.lower() for keyword in urgent_keywords):
            score += priority_weights.get("urgent_keywords", 0.2)

        if any(keyword in body.lower() for keyword in opportunity_keywords):
            score += priority_weights.get("opportunity_keywords", 0.2)

        # Ensure score is between 0 and 1
        return min(1.0, score)

    def _cleanup(self) -> None:
        """Clean up resources before exit."""
        super()._cleanup()

        if self.gmail_sync:
            try:
                self.logger.info("Closing Gmail sync connections...")
                self.gmail_sync.close_connection()
            except Exception as e:
                self.logger.warning("Error closing Gmail sync connection: %s", e)

        # Ensure db_manager connections are closed
        try:
            self.logger.info("Closing database connections...")
            db_manager.close()
        except Exception as e:
            self.logger.warning("Error closing database connections: %s", e)

    def __signal_handler(self, sig, frame):
        """Handle signals like CTRL+C to allow clean shutdown."""
        if not hasattr(self, "_interrupted"):
            self._interrupted = True
            self.logger.info(
                "⏹️ Received interrupt signal, finishing current email before shutdown...",
            )
        else:
            # Second interrupt, exit immediately
            self.logger.warning("⏹️ Forced exit due to second interrupt")
            import sys

            sys.exit(1)

    def _maybe_release_db_connections(self):
        """Periodically release database connections to avoid long locks."""
        try:
            # Import here to avoid circular imports
            from dewey.core.db import db_manager

            # If the db_manager has a close method, call it to release connections
            if hasattr(db_manager, "close"):
                db_manager.close()
                self.logger.debug("Released database connections")
        except Exception as e:
            self.logger.warning(f"Error releasing database connections: {e}")


def main():
    """Main entry point for the unified email processor."""
    try:
        # Setup signal handling for main process
        import signal

        # Create processor instance
        processor = UnifiedEmailProcessor()

        # Define signal handler function
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal, initiating graceful shutdown...")
            processor._interrupted = True

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination

        # Run processor
        processor.execute()

    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Shutting down gracefully...")
    except Exception as e:
        print("Error: %s", e)
        import traceback

        traceback.print_exc()
    finally:
        # Ensure any database connections are properly closed
        try:
            if (
                "processor" in locals()
                and hasattr(processor, "gmail_sync")
                and processor.gmail_sync
            ):
                processor.gmail_sync.close_connection()
        except:
            pass
        # Signal successful exit
        print("Process completed.")


if __name__ == "__main__":
    main()
