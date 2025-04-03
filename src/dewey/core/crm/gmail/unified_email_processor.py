#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from src.dewey.core.base_script import BaseScript
from src.dewey.core.crm.gmail.gmail_sync import GmailSync
from src.dewey.core.db.connection import db_manager


class UnifiedEmailProcessor(BaseScript):
    """Unified processor that handles Gmail sync, enrichment, and prioritization.
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
            from src.dewey.core.crm.gmail.run_gmail_sync import OAuthGmailClient

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
                "Initializing Gmail client with credentials from %s", credentials_path
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
            self.gmail_sync = GmailSync(
                gmail_client=gmail_client, db_path=motherduck_db,
            )

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
                "📨 Found %s emails to process (limiting to %s)", total_count, max_emails
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
                            "❌ Error processing email %s: %s", email_id, str(e), exc_info=True,
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
                    eta_str = "{:.1f} seconds".format(remaining_time)

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
            success_count, processed_count, total_time, processed_count / total_time
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
                                f"ALTER TABLE email_analyses ADD COLUMN {col_name} {col_type} {default_value}",
                                for_write=True,
                            )
                        except Exception as e:
                            self.logger.warning(
                                "Could not add column %s to email_analyses: %s", col_name, e
                            )

                # Try to create indexes if they don't exist
                try:
                    # Check if indexes exist first
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
                        f"Could not create indexes on email_analyses: {e}",
                    )

            except Exception as e:
                self.logger.error(f"Error checking email_analyses columns: {e}")

        # Create contacts table if it doesn't exist
        if "contacts" not in existing_tables:
            self.logger.info("🔃 Creating contacts table")
            try:
                db_manager.execute_query(
                    """
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email VARCHAR UNIQUE NOT NULL,
                        first_name VARCHAR,
                        last_name VARCHAR,
                        full_name VARCHAR,
                        company VARCHAR,
                        job_title VARCHAR,
                        is_client BOOLEAN DEFAULT FALSE,
                        email_count INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confidence_score FLOAT DEFAULT 0.0,
                        linkedin_url VARCHAR,
                        twitter_handle VARCHAR
                    )
                """,
                    for_write=True,
                )

                # Create index on email to optimize lookups
                try:
                    db_manager.execute_query(
                        """
                        CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)
                    """,
                        for_write=True,
                    )
                except Exception as e:
                    self.logger.warning("Could not create index on contacts: %s", e)

            except Exception as e:
                self.logger.error("Error creating contacts table: %s", e)

        # For existing contacts table, check and add missing columns
        if "contacts" in existing_tables:
            try:
                # Get existing columns
                columns_result = db_manager.execute_query(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'contacts'
                """,
                )
                existing_columns = (
                    [row[0].lower() for row in columns_result] if columns_result else []
                )

                # Define expected columns with their types
                expected_columns = {
                    "id": "INTEGER",
                    "email": "VARCHAR",
                    "first_name": "VARCHAR",
                    "last_name": "VARCHAR",
                    "full_name": "VARCHAR",
                    "company": "VARCHAR",
                    "job_title": "VARCHAR",
                    "is_client": "BOOLEAN",
                    "email_count": "INTEGER",
                    "linkedin_url": "VARCHAR",
                    "twitter_handle": "VARCHAR",
                    "confidence_score": "FLOAT",
                    "created_at": "TIMESTAMP",
                    "last_updated": "TIMESTAMP",
                }

                # Check and add missing columns
                for col_name, col_type in expected_columns.items():
                    if col_name.lower() not in existing_columns:
                        self.logger.info(
                            "➕ Adding missing column to contacts: %s", col_name
                        )
                        try:
                            default_value = ""
                            if col_type == "BOOLEAN":
                                default_value = "DEFAULT FALSE"
                            elif col_type == "INTEGER":
                                default_value = "DEFAULT 0"
                            elif col_type == "FLOAT":
                                default_value = "DEFAULT 0.0"
                            elif col_type == "TIMESTAMP":
                                default_value = "DEFAULT CURRENT_TIMESTAMP"

                            db_manager.execute_query(
                                "ALTER TABLE contacts ADD COLUMN {col_name} {col_type} {default_value}".format(col_name=col_name, col_type=col_type, default_value=default_value),
                                for_write=True,
                            )
                        except Exception as e:
                            self.logger.warning(
                                "Could not add column %s to contacts: %s", col_name, e
                            )

                # Try to create index if it doesn't exist
                try:
                    db_manager.execute_query(
                        """
                        CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)
                    """,
                        for_write=True,
                    )
                except Exception as e:
                    self.logger.warning("Could not create index on contacts: %s", e)

            except Exception as e:
                self.logger.error("Error checking contacts columns: %s", e)

        self.logger.info("✅ Database tables and columns verified and created")

    def _get_existing_tables(self) -> list[str]:
        """Get list of existing tables in the database."""
        try:
            # First try DuckDB's information_schema.tables approach
            results = db_manager.execute_query(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'main'
            """,
            )

            if results:
                return [row[0].lower() for row in results]

            # Fallback to SHOW TABLES if the first approach doesn't work
            try:
                results = db_manager.execute_query("SHOW TABLES")
                return [row[0].lower() for row in results] if results else []
            except Exception:
                # Last resort: try PRAGMA table_list which works in SQLite
                try:
                    results = db_manager.execute_query("PRAGMA table_list")
                    return [
                        row[1].lower()
                        for row in results
                        if row[1] not in ("sqlite_master", "sqlite_temp_master")
                    ]
                except Exception as e:
                    self.logger.warning("All table list approaches failed: %s", e)
                    return []

        except Exception as e:
            self.logger.error(f"Error getting table list: {e}")
            return []

    def _get_contact_table_columns(self) -> list[str]:
        """Get the list of column names in the contacts table to support dynamic queries."""
        try:
            columns_result = db_manager.execute_query(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'contacts'
            """,
            )

            # Handle result format properly - each row is a tuple, not a dict
            if columns_result:
                # If we have results, extract the first element of each tuple
                return [row[0] for row in columns_result]
            return []
        except Exception as e:
            self.logger.error(f"Error getting contact table columns: {e}")
            # Return minimal set of expected columns as fallback
            return ["email", "is_client", "last_updated"]

    def _process_single_email(self, email_id):
        """Process a single email for enrichment and storage."""
        try:
            # Skip if already processed
            query = """
                SELECT msg_id FROM email_analyses
                WHERE msg_id = ?
            """
            result = db_manager.execute_query(query, [email_id])

            if result:
                self.logger.debug(
                    "Email %s already in email_analyses, checking if processing is complete",
                    email_id,
                )

                # Check if already fully processed
                status_query = """
                    SELECT status FROM email_analyses
                    WHERE msg_id = ? AND status = 'processed'
                """
                status_result = db_manager.execute_query(status_query, [email_id])

                if status_result:
                    self.logger.debug(
                        "Email %s already fully processed, skipping",
                        email_id,
                    )
                    return True

            # Fetch email if it exists
            raw_email_query = """
                SELECT
                    message_id,
                    thread_id,
                    sender as from_address,
                    subject,
                    internal_date,
                    snippet
                FROM raw_emails
                WHERE message_id = ?
            """
            email_data = db_manager.execute_query(raw_email_query, [email_id])

            if not email_data:
                self.logger.warning("⚠️ Email %s not found in raw_emails", email_id)
                return False

            # Extract raw email data
            (msg_id, thread_id, from_address, subject, internal_date, snippet) = (
                email_data[0]
            )

            # Check contact info
            contact = self._extract_contact_info(from_address, email_id)

            # Additional enrichment through EmailEnrichment if available
            enrichment_data = {}
            if hasattr(self, "enrichment") and self.enrichment:
                try:
                    if hasattr(self.enrichment, "enrich_email"):
                        self.logger.info(
                            "Performing additional enrichment for email %s", email_id
                        )
                        success = self.enrichment.enrich_email(email_id)
                        if success:
                            self.logger.info(
                                "Additional enrichment completed for email %s", email_id
                            )
                        else:
                            self.logger.warning(
                                "Additional enrichment failed for email %s", email_id
                            )
                    else:
                        self.logger.warning(
                            "EmailEnrichment class exists but missing enrich_email method",
                        )
                except Exception as e:
                    self.logger.error(
                        "Error during email enrichment: %s", e, exc_info=True,
                    )

            # Create standardized entry in email_analyses
            self._store_email_analysis(
                msg_id,
                thread_id,
                subject,
                from_address,
                internal_date,
                snippet,
                contact,
            )

            return True

        except Exception as e:
            self.logger.error(
                "❌ Error processing single email %s: %s", email_id, e, exc_info=True,
            )
            return False

    def _extract_contact_info(self, from_address, email_id):
        """Extract contact information from an email.

        Args:
        ----
            from_address: The sender's email address
            email_id: The email ID for reference

        Returns:
        -------
            Dict containing contact information

        """
        try:
            # Start with basic info from the from_address
            contact = {
                "email": from_address,
                "is_client": False,
                "confidence_score": 0.5,
                "source": "gmail",
            }

            # Extract name, if available
            if "<" in from_address and ">" in from_address:
                # Format: "John Doe <john@example.com>"
                name_part = from_address.split("<")[0].strip()
                email_part = from_address.split("<")[1].split(">")[0].strip()

                contact["full_name"] = name_part
                contact["email"] = email_part

                # Try to split into first/last name
                name_parts = name_part.split()
                if len(name_parts) > 0:
                    contact["first_name"] = name_parts[0]
                    if len(name_parts) > 1:
                        contact["last_name"] = " ".join(name_parts[1:])

            # Check for known domain patterns
            if "@" in from_address:
                domain = from_address.split("@")[-1].lower()
                contact["domain"] = domain

                # Check if this is a potential client domain
                client_domains = self.get_config_value("client_domains", [])
                if domain in client_domains:
                    contact["is_client"] = True
                    contact["confidence_score"] = 0.9

            return contact

        except Exception as e:
            self.logger.error("Error extracting contact info from %s: %s", from_address, e)
            return {"email": from_address, "error": str(e)}

    def _get_column_names(self, table_name: str) -> list[str]:
        """Get column names for a table.

        Args:
        ----
            table_name: Name of the table

        Returns:
        -------
            List of column names in lowercase

        """
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Query table schema to get column names
            query = f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """
            result = db_manager.execute_query(query)

            # Extract column names and convert to lowercase
            column_names = [row[0].lower() for row in result] if result else []

            # Fall back to a list of common column names if query fails
            if not column_names:
                self.logger.warning(
                    "Could not get column names, using fallback approach",
                )
                if table_name == "email_analyses":
                    column_names = [
                        "msg_id",
                        "thread_id",
                        "subject",
                        "from_address",
                        "status",
                        "metadata",
                        "priority",
                        "priority_score",
                        "analysis_date",
                        "snippet",
                        "internal_date",
                    ]
                elif table_name == "contacts":
                    column_names = [
                        "email",
                        "first_name",
                        "last_name",
                        "full_name",
                        "company",
                        "job_title",
                        "phone",
                        "country",
                        "source",
                        "domain",
                        "last_interaction_date",
                        "metadata",
                        "is_client",
                    ]

            return column_names

        except Exception as e:
            self.logger.warning(f"Error getting column names for {table_name}: {e}")
            # Return minimal set of columns as fallback
            return ["id", "name", "created_at", "updated_at"]

    def _store_email_analysis(
        self, msg_id, thread_id, subject, from_address, internal_date, snippet, contact,
    ):
        """Store email analysis in the database.

        Args:
        ----
            msg_id: Message ID
            thread_id: Thread ID
            subject: Email subject
            from_address: Sender's email address
            internal_date: Date the email was sent
            snippet: Email snippet
            contact: Contact information dict

        """
        try:
            # Import here to allow connection refreshes
            from dewey.core.db import db_manager

            # Get column names
            column_names = self._get_column_names("email_analyses")

            # Check if record exists
            exists = db_manager.execute_query(
                "SELECT 1 FROM email_analyses WHERE msg_id = ?", [msg_id],
            )

            # Get current timestamp as ISO string for consistency
            now_str = datetime.now().isoformat()
            now_int = int(datetime.now().timestamp())

            # Prepare JSON data
            metadata = json.dumps(
                {"from": from_address, "contact": contact, "processed_at": now_str},
            )

            # Calculate priority score based on contact info
            priority_score = 0.5  # Default score
            if contact.get("is_client", False):
                priority_score = 0.8  # Higher priority for clients

            # Convert to integer scale for priority column (0-100)
            priority_int = int(priority_score * 100)

            # Handle internal_date type - convert to both string and int formats for flexibility
            internal_date_str = None
            internal_date_int = None

            if internal_date:
                try:
                    # If it's a timestamp, convert it
                    if isinstance(internal_date, (int, float)):
                        internal_date_int = int(internal_date)
                        internal_date_str = datetime.fromtimestamp(
                            internal_date_int / 1000
                            if internal_date_int > 1e10
                            else internal_date_int,
                        ).isoformat()
                    # If it's a string, convert to int if possible
                    elif isinstance(internal_date, str):
                        internal_date_str = internal_date
                        try:
                            # Try to parse the string as a datetime
                            dt = datetime.fromisoformat(
                                internal_date.replace("Z", "+00:00"),
                            )
                            internal_date_int = int(dt.timestamp())
                        except:
                            pass
                except Exception as e:
                    self.logger.warning(f"Error converting internal_date: {e}")
                    # Keep the values as they are

            if exists:
                # Update existing record
                try:
                    # Update without timestamp fields to avoid type issues
                    db_manager.execute_query(
                        """
                        UPDATE email_analyses
                        SET
                            thread_id = ?,
                            subject = ?,
                            from_address = ?,
                            priority = ?,
                            priority_score = ?,
                            status = 'processed',
                            metadata = ?
                        WHERE msg_id = ?
                    """,
                        [
                            thread_id,
                            subject,
                            from_address,
                            priority_int,
                            priority_score,
                            metadata,
                            msg_id,
                        ],
                        for_write=True,
                    )

                    self.logger.debug(f"Updated email_analyses record for {msg_id}")

                    # Update timestamp fields separately
                    self._update_timestamp_fields(
                        msg_id, now_str, now_int, column_names,
                    )

                    # Update snippet if present
                    if "snippet" in column_names and snippet:
                        self._update_field(msg_id, "snippet", snippet)

                    # Update internal_date field (always done separately to avoid type issues)
                    self._update_internal_date(
                        msg_id, internal_date_int, internal_date_str, column_names,
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Error updating record, trying simpler update: {e}",
                    )
                    # Check if this was a write-write conflict
                    if "write-write conflict" in str(e):
                        # Set the flag for adaptive delay
                        self.had_write_conflicts = True

                    # Try a minimal update if the full one fails
                    db_manager.execute_query(
                        """
                        UPDATE email_analyses
                        SET status = 'processed'
                        WHERE msg_id = ?
                    """,
                        [msg_id],
                        for_write=True,
                    )
            else:
                # Insert new record - exclude timestamp and internal_date fields from initial insert
                try:
                    # Build a minimal query with only the essential fields
                    essential_fields = [
                        "msg_id",
                        "thread_id",
                        "subject",
                        "from_address",
                        "priority",
                        "priority_score",
                        "metadata",
                    ]

                    # Exclude any fields not present in the schema
                    fields_to_insert = [
                        field
                        for field in essential_fields
                        if field.lower() in column_names
                    ]

                    # Build parameters list first, then use its length for placeholders
                    insert_values = []
                    for field in fields_to_insert:
                        if field == "msg_id":
                            insert_values.append(msg_id)
                        elif field == "thread_id":
                            insert_values.append(thread_id)
                        elif field == "subject":
                            insert_values.append(subject)
                        elif field == "from_address":
                            insert_values.append(from_address)
                        elif field == "priority":
                            insert_values.append(priority_int)
                        elif field == "priority_score":
                            insert_values.append(priority_score)
                        elif field == "metadata":
                            insert_values.append(metadata)

                    # Generate placeholders based on parameter count
                    placeholders = ", ".join(["?" for _ in insert_values])

                    insert_query = f"""
                        INSERT INTO email_analyses (
                            {", ".join(fields_to_insert)}
                        ) VALUES (
                            {placeholders}
                        )
                    """

                    # Execute the insert
                    db_manager.execute_query(
                        insert_query, insert_values, for_write=True,
                    )

                    self.logger.debug(f"Inserted email_analyses record for {msg_id}")

                    # Update timestamp fields separately
                    self._update_timestamp_fields(
                        msg_id, now_str, now_int, column_names,
                    )

                    # Update snippet if present
                    if "snippet" in column_names and snippet:
                        self._update_field(msg_id, "snippet", snippet)

                    # Update internal_date field (always done separately to avoid type issues)
                    self._update_internal_date(
                        msg_id, internal_date_int, internal_date_str, column_names,
                    )

                except Exception as e:
                    self.logger.error(f"Error inserting record with dynamic query: {e}")
                    # Check if this was a write-write conflict
                    if "write-write conflict" in str(e):
                        # Set the flag for adaptive delay
                        self.had_write_conflicts = True

                    # Try an absolute minimal insert as last resort
                    try:
                        db_manager.execute_query(
                            """
                            INSERT INTO email_analyses (
                                msg_id, status
                            ) VALUES (
                                ?, 'processed'
                            )
                        """,
                            [msg_id],
                            for_write=True,
                        )
                        self.logger.warning("Fell back to minimal insert for %s", msg_id)
                    except Exception as e2:
                        self.logger.error("Even minimal insert failed: %s", e2)

            # Update contact info based on extracted data
            try:
                self._enrich_contact_from_email(msg_id, contact)
            except Exception as e:
                self.logger.warning("Error enriching contact from email: %s", e)

        except Exception as e:
            self.logger.error(
                "Error storing email analysis for %s: %s", msg_id, e, exc_info=True,
            )

    def _update_timestamp_fields(
        self, msg_id, timestamp_str, timestamp_int, column_names,
    ):
        """Update timestamp fields separately based on column types."""
        # Update analysis_date if present
        if "analysis_date" in column_names:
            try:
                # First, check the column type
                type_query = """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_name = 'email_analyses'
                    AND column_name = 'analysis_date'
                """
                type_result = db_manager.execute_query(type_query)

                if not type_result:
                    self.logger.warning(
                        "Could not determine column type for analysis_date, skipping update",
                    )
                    return

                col_type = type_result[0][0].upper() if type_result[0][0] else "UNKNOWN"
                self.logger.debug(f"analysis_date column type: {col_type}")

                # For timestamp/date types, use string format
                if any(t in col_type for t in ["TIMESTAMP", "DATETIME", "DATE"]):
                    db_manager.execute_query(
                        """
                        UPDATE email_analyses
                        SET analysis_date = ?
                        WHERE msg_id = ?
                    """,
                        [timestamp_str, msg_id],
                        for_write=True,
                    )
                    self.logger.debug(
                        f"Updated analysis_date with string value: {timestamp_str}",
                    )

                # For numeric types, use integer format
                elif any(t in col_type for t in ["INT", "BIGINT", "INTEGER"]):
                    db_manager.execute_query(
                        """
                        UPDATE email_analyses
                        SET analysis_date = ?
                        WHERE msg_id = ?
                    """,
                        [timestamp_int, msg_id],
                        for_write=True,
                    )
                    self.logger.debug(
                        f"Updated analysis_date with integer value: {timestamp_int}",
                    )

                # For unknown types, skip update to avoid errors
                else:
                    self.logger.warning(
                        f"Unsupported column type for analysis_date: {col_type}, skipping update",
                    )

            except Exception as e:
                self.logger.warning(f"Could not update analysis_date: {e}")

    def _update_internal_date(
        self, msg_id, internal_date_int, internal_date_str, column_names,
    ):
        """Update internal_date field separately, respecting column type."""
        if "internal_date" not in column_names:
            return

        try:
            # First, check the column type in the database
            type_query = """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'email_analyses'
                AND column_name = 'internal_date'
            """
            type_result = db_manager.execute_query(type_query)

            if not type_result:
                self.logger.warning(
                    "Could not determine column type for internal_date, skipping update",
                )
                return

            col_type = type_result[0][0].upper() if type_result[0][0] else "UNKNOWN"
            self.logger.debug(f"internal_date column type: {col_type}")

            # For numeric types, use integer format
            if any(t in col_type for t in ["INT", "BIGINT", "INTEGER"]):
                if internal_date_int is not None:
                    db_manager.execute_query(
                        """
                        UPDATE email_analyses
                        SET internal_date = ?
                        WHERE msg_id = ?
                    """,
                        [internal_date_int, msg_id],
                        for_write=True,
                    )
                    self.logger.debug(
                        f"Updated internal_date with integer value: {internal_date_int}",
                    )
                else:
                    self.logger.warning(
                        "No integer value available for internal_date, skipping update",
                    )

            # For timestamp/date types, use string format
            elif any(t in col_type for t in ["TIMESTAMP", "DATETIME", "DATE"]):
                if internal_date_str:
                    db_manager.execute_query(
                        """
                        UPDATE email_analyses
                        SET internal_date = ?
                        WHERE msg_id = ?
                    """,
                        [internal_date_str, msg_id],
                        for_write=True,
                    )
                    self.logger.debug(
                        f"Updated internal_date with string value: {internal_date_str}",
                    )
                else:
                    self.logger.warning(
                        "No string value available for internal_date, skipping update",
                    )

            # For unknown types, skip update to avoid errors
            else:
                self.logger.warning(
                    f"Unsupported column type for internal_date: {col_type}, skipping update",
                )

        except Exception as e:
            self.logger.warning(f"Could not update internal_date for {msg_id}: {e}")

    def _update_field(self, msg_id, field_name, value):
        """Update a specific field with proper error handling."""
        try:
            db_manager.execute_query(
                f"""
                UPDATE email_analyses
                SET {field_name} = ?
                WHERE msg_id = ?
            """,
                [value, msg_id],
                for_write=True,
            )
        except Exception as e:
            self.logger.warning(f"Could not update {field_name} for {msg_id}: {e}")

    def _enrich_contact_from_email(self, email_id: str, contact_info: dict[str, Any]):
        """Enrich contact information and set priority based on client status."""
        if not contact_info.get("email"):
            self.logger.warning(
                f"No email found for contact in message {email_id}, using sender",
            )
            contact_info["email"] = contact_info.get("sender", f"unknown_{email_id}")

        # Set confidence score if missing
        if "confidence_score" not in contact_info:
            contact_info["confidence_score"] = 0.0

        # Get current timestamp as ISO string
        now_str = datetime.now().isoformat()

        # Prepare simplified contact info without complex structures
        # that might cause issues with database queries
        simple_contact = {
            "email": contact_info["email"],
            "is_client": False,
            "email_count": 1,
            "confidence_score": contact_info.get("confidence_score", 0.0),
        }

        # Add simple string fields
        for field in [
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "company",
            "title",
        ]:
            if contact_info.get(field):
                simple_contact[field] = contact_info[field]

        # Map title to job_title if needed
        if contact_info.get("title") and "job_title" not in simple_contact:
            simple_contact["job_title"] = contact_info["title"]

        # Add LinkedIn/Twitter if available
        if contact_info.get("linkedin_url"):
            simple_contact["linkedin_url"] = contact_info["linkedin_url"]
        if contact_info.get("twitter_handle"):
            simple_contact["twitter_handle"] = contact_info["twitter_handle"]

        # Check if the contact is a client
        try:
            is_client_result = db_manager.execute_query(
                """
                SELECT 1 FROM client_profiles
                WHERE email = ? LIMIT 1
            """,
                [simple_contact["email"]],
            )

            # If this is a client, add a 0.3 to confidence score
            client_match = len(is_client_result) > 0
            simple_contact["is_client"] = client_match
            if client_match:
                simple_contact["confidence_score"] = min(
                    1.0, simple_contact["confidence_score"] + 0.3,
                )
                contact_info["is_client"] = True
                contact_info["confidence_score"] = simple_contact["confidence_score"]
        except Exception as e:
            self.logger.warning("Error checking client status: %s", e)

        # Get existing columns to ensure we're using the right field names
        try:
            # Check if contact already exists - use a more resilient query
            contact_exists = False
            try:
                # First try a simple existence check
                existing = db_manager.execute_query(
                    """
                    SELECT 1 FROM contacts WHERE email = ? LIMIT 1
                """,
                    [simple_contact["email"]],
                )
                contact_exists = len(existing) > 0
            except Exception as e:
                self.logger.warning(f"Error checking existing contact: {e}")
                # Fallback to a different check
                try:
                    existing = db_manager.execute_query(
                        """
                        SELECT COUNT(*) FROM contacts WHERE email = ?
                    """,
                        [simple_contact["email"]],
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
                        "Updated existing contact: %s", simple_contact["email"]
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
                            "Both update attempts failed for contact %s: %s", simple_contact["email"], e2
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
                                "Could not update additional contact info: %s", e
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
                            "All insert attempts failed for %s: %s", simple_contact["email"], e2
                        )
        except Exception as e:
            self.logger.error("Error enriching contact from email: %s", e, exc_info=True)

    def _calculate_priority_score(
        self, contact_info: dict[str, Any], body: str
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
