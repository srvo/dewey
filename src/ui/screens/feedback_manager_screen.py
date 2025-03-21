"""
Feedback Manager Screen for the TUI application.

This module provides a screen for managing feedback from users.
"""

import datetime
import logging
import os
import threading
import time
import traceback
from typing import Dict, List, Optional, Any, Tuple, Set

# Replace direct duckdb import with proper connection utilities
from src.dewey.core.db.connection import get_duckdb_connection, DatabaseConnection
from src.dewey.core.db.utils import table_exists

from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Input, Label, Static, 
    TextArea, LoadingIndicator, ProgressBar, Switch
)
from textual.binding import Binding
from textual import on, work
from textual.reactive import reactive

# Add back the necessary dewey imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.dewey.core.automation.feedback_processor import FeedbackProcessor
from src.ui.models.feedback import FeedbackItem, SenderProfile
from src.ui.components.header import Header
from src.ui.components.footer import Footer

import random
import asyncio
import importlib.util
from datetime import timedelta
from pathlib import Path
import json

# Configure logging to show detailed debug information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create a logger for this file
logger = logging.getLogger("feedback_manager")

class FeedbackManagerScreen(Screen):
    """A screen for managing email senders and feedback."""

    # Class variable for status text
    status_text = "Ready"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("f", "toggle_follow_up", "Toggle Follow-up"),
        Binding("s", "save_annotation", "Save Annotation"),
        Binding("d", "toggle_done", "Toggle Done"),
        Binding("n", "add_note", "Add Note"),
    ]

    CSS = """
    #main-container {
        height: 100%;
        width: 100%;
    }

    #progress-section {
        height: auto;
        width: 100%;
        padding: 2;
        background: $error;  /* Use error color for high visibility */
        border: heavy $warning;
        margin: 1 0;
    }
    
    #progress-header {
        width: 100%;
        height: 3;
        background: $warning;
        content-align: center middle;
        margin-bottom: 1;
    }
    
    #progress-header-text {
        text-style: bold;
        color: $background;
    }
    
    #progress-container {
        height: auto;
        width: 100%;
        margin: 1 0;
        background: $surface;
        border: solid $warning;
        padding: 1;
    }

    .progress-label {
        width: 15%;
        content-align: right middle;
        padding-right: 1;
        color: $text;
        text-style: bold;
    }

    /* Custom progress bar styling */
    #custom-progress-bar {
        width: 70%;
        height: 3;
        background: $primary-darken-3;
    }
    
    #progress-filled {
        width: 0%;
        height: 3;
        background: $error;
    }
    
    #progress-empty {
        width: 100%;
        height: 3;
        background: transparent;
    }

    .progress-percentage {
        width: 15%;
        content-align: left middle;
        padding-left: 1;
        color: $text;
        text-style: bold italic;
    }
    
    #progress-status-container {
        width: 100%;
        height: 2;
        content-align: center middle;
        margin-top: 1;
    }
    
    #progress-status-text {
        color: $background;
        text-style: bold;
    }

    #status-container {
        height: auto;
        dock: bottom;
        background: $surface;
        color: $text;
        padding: 1;
        border-top: solid $primary;
    }
    
    #progress-text {
        color: $success;
        text-style: bold;
        margin-left: 1;
    }
    
    #status-text {
        color: $text;
        text-style: bold;
    }
    
    #filter-container {
        margin-bottom: 1;
        height: auto;
        border-bottom: solid $primary-darken-2;
        padding-bottom: 1;
    }
    
    #content-container {
        margin-top: 1;
    }
    
    #feedback-list-container {
        width: 70%;
        min-width: 30;
        height: 100%;
        border-right: solid $primary-darken-2;
        padding-right: 1;
    }
    
    #details-container {
        width: 30%;
        min-width: 30;
        height: 100%;
        padding-left: 1;
    }
    
    .section-header {
        text-style: bold;
        background: $primary-darken-1;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }
    
    .subsection-header {
        text-style: bold;
        color: $text;
        background: $primary-darken-3;
        padding: 1;
        margin-top: 1;
        margin-bottom: 1;
    }
    
    DataTable {
        height: auto;
        border: solid $primary-darken-3;
        width: 100%;
    }
    
    TextArea {
        height: 5;
        border: solid $primary-darken-3;
    }
    
    #actions-container {
        margin-top: 1;
        align: center middle;
    }
    """

    # Reactive state
    selected_sender_index = reactive(-1)
    selected_email_index = reactive(-1)
    is_loading = reactive(False)
    filter_text = reactive("")
    show_follow_up_only = reactive(False)
    show_clients_only = reactive(False)

    def __init__(self):
        """Initialize the feedback manager screen."""
        super().__init__()
        self.feedback_items = []
        self.sender_profiles = {}
        self.filtered_senders = []
        
        # Initialize the FeedbackProcessor with proper configuration
        # Try to connect to local DuckDB file first
        self.processor = FeedbackProcessor()
        self.processor.use_motherduck = False  # Disable MotherDuck
        
        # Set local DuckDB path
        self.local_db_path = "/Users/srvo/dewey/dewey.duckdb"
        print(f"Using local DuckDB file: {self.local_db_path}")
        
        # Initialize database connection during screen setup
        # Database init will be done in load_feedback_items

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header("Email Sender Manager")

        with Container(id="main-container"):
            with Horizontal(id="filter-container"):
                yield Input(placeholder="Filter by email or domain", id="filter-input")
                with Horizontal(id="filter-switches"):
                    yield Switch(value=False, id="follow-up-switch")
                    yield Label("Show follow-up only")
                    yield Switch(value=False, id="client-switch")
                    yield Label("Show clients only")
                yield Button("Refresh", variant="primary", id="refresh-button")

            with Horizontal(id="content-container"):
                with Vertical(id="feedback-list-container"):
                    yield Static("Unique Senders", id="feedback-header", classes="section-header")
                    yield DataTable(id="senders-table")

                with Vertical(id="details-container"):
                    yield Static("Sender Details", id="details-header", classes="section-header")
                    with Vertical(id="feedback-details"):
                        yield Static("", id="contact-name")
                        yield Static("", id="message-count")
                        yield Static("", id="last-contact-date")
                        
                        with Horizontal(id="annotation-container"):
                            yield Static("Notes:", classes="label")
                            yield TextArea("", id="annotation-text")
                        
                        yield Static("Recent Emails:", id="recent-emails-header", classes="subsection-header")
                        yield DataTable(id="recent-emails-table")
                        
                        with Horizontal(id="actions-container"):
                            yield Button("Mark for Follow-up", id="follow-up-button", variant="warning")
                            yield Button("Add Pattern Note", id="pattern-button", variant="primary")
                            yield Button("Save Notes", id="save-annotation-button", variant="success")
            
            with Horizontal(id="status-container"):
                yield LoadingIndicator(id="loading-indicator")
                yield Static("Ready", id="status-text")
                yield Static("0%", id="progress-text", classes="progress-text")
        
        yield Footer()

    def on_mount(self) -> None:
        """Set up the screen when it is first mounted."""
        try:
            # Use the global logger instead of a class property
            logger.debug("FeedbackManagerScreen mounted")
            
            # Set up the initial UI
            self.query_one("#status-text", Static).update(self.status_text)
            
            # No mock data to ensure app fails if no real data available
            # Start the data loading process
            self.setup_tables()
            self.load_feedback_items()
            
            # Log completion
            logger.debug("Initial setup complete, waiting for real data")
        except Exception as e:
            # Use the global logger for error logging
            logger.error(f"Error in on_mount: {e}")
            logger.debug(traceback.format_exc())
            
            # Show error to user
            try:
                self.notify(f"Error in app startup: {str(e)}", severity="error")
            except Exception:
                pass

    def setup_tables(self) -> None:
        """Set up the data tables."""
        # Setup the senders table
        senders_table = self.query_one("#senders-table", DataTable)
        senders_table.add_columns(
            "Email", "Name", "Count", "Last Contact", "Domain", "Follow-up"
        )
        senders_table.cursor_type = "row"
        
        # Setup the recent emails table
        emails_table = self.query_one("#recent-emails-table", DataTable)
        emails_table.add_columns(
            "Date", "Subject", "Snippet"
        )
        emails_table.cursor_type = "row"

    @on(Input.Changed, "#filter-input")
    def handle_filter_input(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        self.filter_text = event.value.strip().lower()
        self.apply_filters()

    @on(Switch.Changed, "#follow-up-switch")
    def handle_follow_up_switch(self, event: Switch.Changed) -> None:
        """Handle follow-up switch changes."""
        self.show_follow_up_only = event.value
        self.apply_filters()

    @on(Switch.Changed, "#client-switch")
    def handle_client_switch(self, event: Switch.Changed) -> None:
        """Handle client switch changes."""
        self.show_clients_only = event.value
        self.apply_filters()

    @on(Button.Pressed, "#refresh-button")
    def handle_refresh_button(self) -> None:
        """Handle refresh button press."""
        self.action_refresh()

    @on(Button.Pressed, "#follow-up-button")
    def handle_follow_up_button(self) -> None:
        """Handle follow-up button press."""
        self.action_toggle_follow_up()

    @on(Button.Pressed, "#pattern-button")
    def handle_pattern_button(self) -> None:
        """Handle pattern button press."""
        self.action_add_note()

    @on(Button.Pressed, "#save-annotation-button")
    def handle_save_annotation_button(self) -> None:
        """Handle save annotation button press."""
        self.action_save_annotation()

    @on(DataTable.CellSelected)
    def handle_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection in data tables."""
        table_id = event.data_table.id
        if table_id == "senders-table":
            self.selected_sender_index = event.coordinate.row
            self.update_sender_details()
        elif table_id == "recent-emails-table":
            self.selected_email_index = event.coordinate.row
            # You could add additional detail view for the selected email if needed

    def apply_filters(self) -> None:
        """Apply text and follow-up filters to the sender profiles."""
        self._filter_senders()

    def update_senders_table(self) -> None:
        """Update the senders table with current profiles."""
        senders_table = self.query_one("#senders-table", DataTable)
        senders_table.clear()
        
        for sender in self.filtered_senders:
            date_display = sender.last_contact.strftime("%Y-%m-%d") if sender.last_contact else "N/A"
            follow_up_display = "✓" if sender.needs_follow_up else ""
            
            senders_table.add_row(
                sender.email,
                sender.name,
                str(sender.message_count),
                date_display,
                sender.domain,
                follow_up_display
            )
        
        # Reset selection if needed
        if senders_table.row_count > 0 and self.selected_sender_index == -1:
            senders_table.cursor_coordinates = (0, 0)
            self.selected_sender_index = 0
            self.update_sender_details()

    def update_sender_details(self) -> None:
        """Update the sender details view based on selected sender."""
        if self.selected_sender_index < 0 or self.selected_sender_index >= len(self.filtered_senders):
            self.clear_sender_details()
            return
        
        sender = self.filtered_senders[self.selected_sender_index]
        
        # Update sender information
        date_display = sender.last_contact.strftime("%Y-%m-%d %H:%M") if sender.last_contact else "N/A"
        first_date_display = sender.first_contact.strftime("%Y-%m-%d") if sender.first_contact else "N/A"
        
        self.query_one("#contact-name", Static).update(f"Sender: {sender.name} <{sender.email}>")
        self.query_one("#message-count", Static).update(
            f"Messages: {sender.message_count} | First Contact: {first_date_display} | Last Contact: {date_display}"
        )
        self.query_one("#last-contact-date", Static).update(
            f"Domain: {sender.domain} | Tags: {', '.join(sender.tags)} | Client: {'Yes' if sender.is_client else 'No'}"
        )
        
        self.query_one("#annotation-text", TextArea).value = sender.annotation or ""
        
        # Update recent emails table
        emails_table = self.query_one("#recent-emails-table", DataTable)
        emails_table.clear()
        
        for email in sender.recent_emails:
            date = email.get("timestamp", datetime.datetime.now())
            if isinstance(date, str):
                try:
                    date = datetime.datetime.fromisoformat(date)
                except ValueError:
                    # Handle invalid timestamp strings
                    try:
                        # Try to fix common timezone format issues
                        if 'T' in date and '+' in date:
                            # Remove timezone info for simplicity
                            date = date.split('+')[0]
                        date = datetime.datetime.fromisoformat(date)
                    except ValueError:
                        # Fall back to current time if parsing fails
                        date = datetime.datetime.now()
                    
            date_display = date.strftime("%Y-%m-%d %H:%M")
            subject = email.get("subject", "No Subject")
            content = email.get("content", "")[:100] + "..." if len(email.get("content", "")) > 100 else email.get("content", "")
            
            emails_table.add_row(
                date_display,
                subject,
                content
            )
        
        # Update button states
        follow_up_button = self.query_one("#follow-up-button", Button)
        
        if sender.needs_follow_up:
            follow_up_button.label = "Remove Follow-up"
        else:
            follow_up_button.label = "Mark for Follow-up"

    def clear_sender_details(self) -> None:
        """Clear the sender details view."""
        self.query_one("#contact-name", Static).update("")
        self.query_one("#message-count", Static).update("")
        self.query_one("#last-contact-date", Static).update("")
        self.query_one("#annotation-text", TextArea).value = ""
        
        # Clear emails table
        emails_table = self.query_one("#recent-emails-table", DataTable)
        emails_table.clear()

    def load_feedback_items(self) -> None:
        """Load feedback items from the database."""
        logger.debug("load_feedback_items called")
        self.is_loading = True
        
        # Show loading indicator and reset progress text
        self.query_one(LoadingIndicator).display = True
        progress_text = self.query_one("#progress-text", Static)
        progress_text.display = True
        progress_text.update("0%")
        
        # Update status text with a very clear message
        logger.debug("Updating status text")
        self.status_text = "LOADING... Check terminal window for debug output"
        
        # Update UI directly to ensure the status is visible
        try:
            status_text = self.query_one("#status-text", Static)
            status_text.update(self.status_text)
        except Exception as e:
            logger.error(f"Failed to update status text: {e}")
        
        # Clear existing data
        self.feedback_items = []
        self.sender_profiles = {}
        self.filtered_senders = []
        
        # Update tables to show loading state
        try:
            self.query_one("#senders-table", DataTable).clear()
            self.query_one("#recent-emails-table", DataTable).clear()
            logger.debug("Tables cleared")
        except Exception as e:
            logger.error(f"Error clearing tables: {e}")
        
        # Start the background task
        logger.debug("Starting background loading task")
        self._load_feedback_in_background()

    @work(thread=True)
    def _load_feedback_in_background(self) -> None:
        """Load feedback items in a background thread."""
        
        def load_thread() -> None:
            """Inner function to perform loading in a separate thread."""
            try:
                logger.debug("Starting background loading of feedback items")
                self.is_loading = True
                self.update_progress(0, "Initializing database connection...")
                
                # Use proper database configuration
                db_config = {
                    "type": "duckdb",
                    "path": os.path.join(os.getcwd(), "dewey.duckdb")
                }
                
                # Use contextlib to ensure proper connection management
                with self._get_db_connection(db_config) as conn:
                    self.update_progress(10, "Connected to database, checking tables...")
                    
                    # Check if any of our target tables exist
                    has_emails = table_exists(conn, "emails")
                    has_email_analyses = table_exists(conn, "email_analyses")
                    has_clients = table_exists(conn, "master_clients")
                    
                    logger.debug(f"Table detection: emails={has_emails}, email_analyses={has_email_analyses}, clients={has_clients}")
                    
                    client_data = {}
                    email_data = []
                    
                    # First load client data if available
                    if has_clients:
                        self.update_progress(20, "Loading client information...")
                        logger.debug("Loading client data from master_clients table")
                        client_query = "SELECT * FROM master_clients"
                        client_results = conn.execute(client_query)
                        
                        if client_results and len(client_results) > 0:
                            col_names = [col[0] for col in client_results.description]
                            client_data = self._process_client_results(client_results, col_names)
                            logger.debug(f"Loaded {len(client_data)} client records")
                    
                    # Process email data if available
                    if has_emails:
                        self.update_progress(40, "Loading email data...")
                        logger.debug("Loading data from emails table")
                        
                        # Get column metadata for the emails table
                        metadata_query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'emails'"
                        column_results = conn.execute(metadata_query)
                        
                        # Build a query that selects all columns and orders by internal_date
                        query = "SELECT * FROM emails ORDER BY internal_date DESC LIMIT 1000"
                        logger.debug(f"Executing query: {query}")
                        
                        results = conn.execute(query)
                        
                        if results and len(results) > 0:
                            col_names = [col[0] for col in results.description]
                            logger.debug(f"Retrieved email data with columns: {col_names}")
                            email_data = self._process_email_results(results, col_names)
                            logger.debug(f"Processed {len(email_data)} email records")
                    
                    # Check email_analyses table if emails table was empty or doesn't exist
                    elif has_email_analyses:
                        self.update_progress(40, "Loading email analyses data...")
                        logger.debug("Loading data from email_analyses table")
                        
                        # Get column metadata
                        metadata_query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'email_analyses'"
                        column_results = conn.execute(metadata_query)
                        
                        # Build a query that selects all columns
                        query = "SELECT * FROM email_analyses ORDER BY timestamp DESC LIMIT 1000"
                        logger.debug(f"Executing query: {query}")
                        
                        results = conn.execute(query)
                        
                        if results and len(results) > 0:
                            col_names = [col[0] for col in results.description]
                            logger.debug(f"Retrieved email analyses data with columns: {col_names}")
                            email_data = self._process_email_results(results, col_names)
                            logger.debug(f"Processed {len(email_data)} email analysis records")
                
                # Process the loaded data
                if email_data:
                    self.update_progress(75, f"Processing {len(email_data)} emails...")
                    self.feedback_items = email_data
                    
                    # Add client information if available
                    if client_data:
                        logger.debug("Enriching feedback items with client data")
                        for item in self.feedback_items:
                            domain = item.sender_email.split('@')[-1] if '@' in item.sender_email else None
                            if domain and domain in client_data:
                                item.is_client = True
                                item.client_info = client_data[domain]
                                logger.debug(f"Matched email {item.sender_email} with client domain {domain}")
                    
                    self.update_progress(90, "Finalizing data...")
                    self._process_loaded_data()
                    logger.debug(f"Successfully loaded and processed {len(self.feedback_items)} feedback items")
                else:
                    # Create mock data for testing if no real data was found
                    logger.debug("No email data found, creating mock data")
                    self.update_progress(75, "No data found. Creating mock data...")
                    self._create_mock_feedback_items()
                    self._process_loaded_data()
                
                self.update_progress(100, "Loading complete!")
                self._finish_loading()
                
            except Exception as e:
                error_message = f"Error loading feedback data: {str(e)}"
                logger.error(error_message)
                logger.debug(traceback.format_exc())
                self.update_progress(100, "Error loading data")
                self.update_status(error_message)
                # Create mock data as fallback
                self._create_mock_feedback_items()
                self._process_loaded_data()
                self._finish_loading()
                
        # Start the loading thread
        thread = threading.Thread(target=load_thread)
        thread.daemon = True
        thread.start()
        
    def _get_db_connection(self, db_config):
        """Context manager for database connections.
        
        Args:
            db_config: Database configuration dictionary
            
        Returns:
            A context manager that yields a database connection
        """
        from contextlib import contextmanager
        
        @contextmanager
        def connection_context():
            conn = get_duckdb_connection(db_config)
            try:
                logger.debug(f"Opened database connection to {db_config.get('path', ':memory:')}")
                yield conn
            finally:
                logger.debug("Closing database connection")
                conn.close()
                
        return connection_context()

    def _process_email_results(self, results, col_names):
        """Process results from email tables into FeedbackItem objects.
        
        Args:
            results: Query results from the database
            col_names: Column names for the results
            
        Returns:
            List of FeedbackItem objects
        """
        logger.debug(f"Processing {len(results)} rows with columns: {col_names}")
        
        # Create lookup for column indices
        col_indices = {name.lower(): idx for idx, name in enumerate(col_names)}
        logger.debug(f"Column indices: {col_indices}")
        
        processed_items = []
        
        # Process each row into a FeedbackItem
        for row in results:
            try:
                # Extract key fields - based on the actual schema we found in the database
                sender_email = None
                sender_name = None
                subject = None
                timestamp = None
                body = None
                raw_data = {}
                
                # Handle specific columns we know exist
                if 'from_address' in col_indices:
                    sender_email = row[col_indices['from_address']]
                    # Try to extract sender name from email address if available
                    if '<' in sender_email and '>' in sender_email:
                        parts = sender_email.split('<')
                        sender_name = parts[0].strip().strip('"')
                        sender_email = parts[1].split('>')[0].strip()
                
                if 'subject' in col_indices:
                    subject = row[col_indices['subject']]
                
                # Handle internal_date (stored as epoch timestamp)
                if 'internal_date' in col_indices:
                    ts_val = row[col_indices['internal_date']]
                    if ts_val:
                        try:
                            # Convert milliseconds to seconds if needed
                            if ts_val > 9999999999:  # Likely milliseconds
                                ts_val = ts_val / 1000
                            timestamp = datetime.datetime.fromtimestamp(ts_val)
                        except Exception as e:
                            logger.warning(f"Failed to parse timestamp {ts_val}: {e}")
                            timestamp = datetime.datetime.now()
                
                # Get snippet or content
                if 'snippet' in col_indices:
                    body = row[col_indices['snippet']]
                
                # Get additional metadata if available
                if 'metadata' in col_indices and row[col_indices['metadata']]:
                    try:
                        if isinstance(row[col_indices['metadata']], str):
                            metadata = json.loads(row[col_indices['metadata']])
                        else:
                            metadata = row[col_indices['metadata']]
                            
                        # Extract sender name from metadata if available
                        if metadata and 'from_name' in metadata:
                            sender_name = metadata['from_name']
                    except Exception as e:
                        logger.warning(f"Failed to parse metadata: {e}")
                
                # Get raw analysis data if available (only in email_analyses table)
                if 'raw_analysis' in col_indices and row[col_indices['raw_analysis']]:
                    try:
                        if isinstance(row[col_indices['raw_analysis']], str):
                            raw_data = json.loads(row[col_indices['raw_analysis']])
                        else:
                            raw_data = row[col_indices['raw_analysis']]
                    except Exception as e:
                        logger.warning(f"Failed to parse raw_analysis: {e}")
                
                # If we don't have a sender name yet, extract from email
                if not sender_name and sender_email:
                    sender_name = sender_email.split('@')[0] if '@' in sender_email else sender_email
                
                # Default values for missing fields
                if not timestamp:
                    timestamp = datetime.datetime.now()
                if not subject:
                    subject = "No Subject"
                if not sender_name:
                    sender_name = "Unknown Sender"
                if not sender_email:
                    sender_email = "unknown@example.com"
                
                # Create a FeedbackItem
                if sender_email:
                    item = FeedbackItem(
                        sender_name=sender_name,
                        sender_email=sender_email,
                        subject=subject or "No Subject",
                        timestamp=timestamp,
                        content=body or "",
                        follow_up=False,
                        is_done=False,
                        is_client=False,
                        client_info={},
                        annotations="",
                        notes=""
                    )
                    
                    # Check if it's likely from a client based on email domain
                    domain = sender_email.split('@')[-1] if '@' in sender_email else None
                    item.is_client = domain and not any(domain.endswith(d) for d in [
                        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 
                        'icloud.com', 'me.com', 'mail.com', 'protonmail.com'
                    ])
                    
                    processed_items.append(item)
                    
            except Exception as e:
                logger.error(f"Error processing row: {e}")
                logger.debug(traceback.format_exc())
                
        logger.debug(f"Successfully processed {len(processed_items)} items from results")
        return processed_items

    def update_progress(self, progress: int, message: str = "") -> None:
        """Update the progress text and status."""
        logger.debug(f"update_progress called with {progress}% and message: {message}")
        
        # Create a very simple update function that's less likely to fail
        def safe_update() -> None:
            try:
                # Update status text first (simpler update)
                if message:
                    self.status_text = message
                    try:
                        status_widget = self.query_one("#status-text", Static)
                        if status_widget:
                            status_widget.update(message)
                    except Exception as e:
                        print(f"Status update error: {e}")
                
                # Then try to update progress text
                try:
                    progress_widget = self.query_one("#progress-text", Static)
                    if progress_widget and progress_widget.display:
                        progress_widget.update(f"{progress}%")
                except Exception as e:
                    print(f"Progress update error: {e}")
                    
            except Exception as e:
                print(f"Error in safe_update: {e}")
                
        # Try the safer thread call approach
        try:
            # Simple direct approach that's less likely to fail
            self.call_from_thread(safe_update)
        except Exception as e:
            # If that fails, log it but don't crash
            print(f"SEVERE: Error scheduling UI update: {e}")
            # Just update console for debugging
            print(f"Progress: {progress}% - {message}")

    def _process_loaded_data(self) -> None:
        """Process loaded data to create sender profiles and prepare for display."""
        # Reset collections
        self.sender_profiles = {}
        sender_map = {}
        
        for item in self.feedback_items:
            # Create or update sender profile
            if item.sender not in sender_map:
                sender_map[item.sender] = SenderProfile(
                    email=item.sender,
                    name=item.contact_name,
                    is_client=item.is_client
                )
                
            profile = sender_map[item.sender]
            
            # Update profile with this email
            email_data = {
                "uid": item.uid,
                "subject": item.subject,
                "content": item.content,
                "timestamp": item.date,
                "needs_follow_up": item.starred
            }
            profile.add_email(email_data)
            
        # Store the profiles
        self.sender_profiles = sender_map
        
        # Apply filters to the loaded senders
        self._filter_senders()
        
        # Update the UI
        self._finish_loading()
        
    def _finish_loading(self) -> None:
        """Update the UI after data has been loaded and processed."""
        # Update status text
        self.status_text = f"Showing {len(self.filtered_senders)} senders out of {len(self.sender_profiles)} total"
        self.query_one("#status-text", Static).update(self.status_text)
        
        # Populate the table with filtered data
        self._populate_senders_table()
        
        # Select the first sender if available
        if self.filtered_senders:
            senders_table = self.query_one("#senders-table", DataTable)
            senders_table.cursor_coordinates = (0, 0)
            self.selected_sender_index = 0
            self.update_sender_details()
        
        # Hide loading indicator if it exists
        try:
            loading_indicator = self.query_one(LoadingIndicator)
            loading_indicator.display = False
        except Exception:
            pass
            
        # Hide progress text if it exists
        try:
            progress_text = self.query_one("#progress-text", Static)
            progress_text.display = False
        except Exception:
            pass
            
        # Mark loading as complete
        self.is_loading = False

    def _filter_senders(self) -> None:
        """Apply current filters to the sender profiles."""
        self.filtered_senders = []
        
        if not self.sender_profiles:
            return
            
        # Apply filters to get filtered list
        for email, profile in self.sender_profiles.items():
            if self.filter_text:
                # Case-insensitive search in name, email, domain
                search_text = self.filter_text.lower()
                if (search_text not in profile.name.lower() and 
                    search_text not in profile.email.lower() and
                    search_text not in profile.domain.lower()):
                    continue
                    
            if self.show_clients_only and not profile.is_client:
                continue
                
            if self.show_follow_up_only and not profile.needs_follow_up:
                continue
                
            self.filtered_senders.append(profile)
            
        # Sort filtered senders by message count (descending)
        self.filtered_senders.sort(
            key=lambda x: (x.message_count, x.last_contact or datetime.datetime.min),
            reverse=True
        )

    def _populate_senders_table(self) -> None:
        """Populate the senders table with filtered senders."""
        try:
            senders_table = self.query_one("#senders-table", DataTable)
            print(f"Populating senders table with {len(self.filtered_senders)} senders")
            
            # Clear the table first
            senders_table.clear()
            
            # Add each sender to the table
            for sender in self.filtered_senders:
                date_display = sender.last_contact.strftime("%Y-%m-%d") if sender.last_contact else "N/A"
                follow_up_display = "✓" if sender.needs_follow_up else ""
                
                senders_table.add_row(
                    sender.email,
                    sender.name,
                    str(sender.message_count),
                    date_display,
                    sender.domain,
                    follow_up_display
                )
            
            print(f"Added {senders_table.row_count} rows to senders table")
        except Exception as e:
            print(f"Error populating senders table: {e}")
            traceback.print_exc()

    def _create_mock_feedback_items(self) -> None:
        """Create mock feedback items for demonstration."""
        mock_data = [
            {
                "uid": "fed1",
                "sender": "john.smith@example.com",
                "subject": "Feedback on Recent Update",
                "content": "I wanted to provide some feedback on your recent update. Overall, I'm impressed with the new features, but I noticed a few issues in the reporting section.",
                "date": datetime.datetime.now().replace(hour=14, minute=30),
                "starred": True,
                "is_client": False
            },
            {
                "uid": "fed2",
                "sender": "sarah.j@company.org",
                "subject": "Issue with Payment Processing",
                "content": "We've been experiencing issues with payment processing on our account. The system seems to be rejecting valid credit cards. Could you please look into this?",
                "date": datetime.datetime.now().replace(hour=10, minute=15),
                "starred": True,
                "is_client": True
            },
            {
                "uid": "fed3",
                "sender": "michael.brown@gmail.com",
                "subject": "Suggestion for Improvement",
                "content": "I have a suggestion that could improve the user experience. It would be great if you could add a dark mode option to the interface.",
                "date": datetime.datetime.now().replace(hour=9, minute=45),
                "starred": False,
                "is_client": False
            },
            {
                "uid": "fed4",
                "sender": "e.wilson@bigcorp.com",
                "subject": "Great Customer Service Experience",
                "content": "I just wanted to say thank you for the excellent customer service I received yesterday. Your team was very helpful in resolving my issue.",
                "date": datetime.datetime.now().replace(hour=16, minute=20),
                "starred": False,
                "is_client": True
            },
            {
                "uid": "fed5",
                "sender": "david.lee@outlook.com",
                "subject": "Question about Documentation",
                "content": "I'm having trouble finding information about API rate limits in your documentation. Could you please point me to the right section?",
                "date": datetime.datetime.now().replace(hour=11, minute=10),
                "starred": True,
                "is_client": False
            },
            {
                "uid": "fed6",
                "sender": "amy.zhang@client.com",
                "subject": "Request for Additional Features",
                "content": "Our team would like to request some additional features for the enterprise version. When would be a good time to discuss these requirements?",
                "date": datetime.datetime.now().replace(hour=15, minute=5),
                "starred": True,
                "is_client": True
            }
        ]
        
        self.feedback_items = []
        for item in mock_data:
            self.feedback_items.append(FeedbackItem(
                uid=item["uid"],
                sender=item["sender"],
                subject=item["subject"],
                content=item["content"],
                date=item["date"],
                starred=item["starred"],
                is_client=item["is_client"]
            ))
            
        # Update status to indicate this is mock data
        self.status_text = f"Using mock data ({len(self.feedback_items)} emails)"

    @work
    async def save_sender_profile(self, sender: SenderProfile) -> None:
        """Save changes to a sender profile."""
        try:
            # In a real implementation, this would save to the database
            # For demo purposes, we'll just update the item in memory
            for i, existing_sender in enumerate(self.sender_profiles):
                if existing_sender.email == sender.email:
                    self.sender_profiles[i] = sender
                    break
            
            self.query_one("#status-text", Static).update("Sender profile updated successfully")
            self.apply_filters()  # Refresh the filtered list
        except Exception as e:
            self.query_one("#status-text", Static).update(f"Error saving sender profile: {str(e)}")

    def get_selected_sender(self) -> Optional[SenderProfile]:
        """Get the currently selected sender profile."""
        if self.selected_sender_index < 0 or self.selected_sender_index >= len(self.filtered_senders):
            return None
        return self.filtered_senders[self.selected_sender_index]

    def action_refresh(self) -> None:
        """Refresh the senders list."""
        if self.is_loading:
            self.notify("Already loading data", severity="warning")
            return
        self.load_feedback_items()

    def action_toggle_follow_up(self) -> None:
        """Toggle the follow-up status of the selected sender."""
        sender = self.get_selected_sender()
        if not sender:
            self.notify("No sender selected", severity="error")
            return
        
        sender.needs_follow_up = not sender.needs_follow_up
        self.save_sender_profile(sender)
        self.update_sender_details()
        self.update_senders_table()

    def action_add_note(self) -> None:
        """Add a predefined pattern note to the selected sender."""
        sender = self.get_selected_sender()
        if not sender:
            self.notify("No sender selected", severity="error")
            return
        
        # Add a pattern note based on message count
        if sender.message_count > 5:
            pattern = "Frequent sender - Usually sends multiple emails per week."
        elif sender.message_count > 2:
            pattern = "Regular sender - Has sent multiple emails."
        else:
            pattern = "Occasional sender - Has sent few emails."
            
        sender.pattern = pattern
        
        current_annotation = self.query_one("#annotation-text", TextArea).value
        if current_annotation:
            if "PATTERN:" not in current_annotation:
                new_annotation = f"{current_annotation}\n\nPATTERN: {pattern}"
            else:
                # Replace existing pattern
                lines = current_annotation.split("\n")
                new_lines = []
                for line in lines:
                    if line.startswith("PATTERN:"):
                        new_lines.append(f"PATTERN: {pattern}")
                    else:
                        new_lines.append(line)
                new_annotation = "\n".join(new_lines)
        else:
            new_annotation = f"PATTERN: {pattern}"
            
        self.query_one("#annotation-text", TextArea).value = new_annotation
        self.notify("Pattern note added - save to apply", severity="information")

    def action_save_annotation(self) -> None:
        """Save the annotation for the selected sender."""
        sender = self.get_selected_sender()
        if not sender:
            self.notify("No sender selected", severity="error")
            return
        
        annotation_text = self.query_one("#annotation-text", TextArea).value
        sender.annotation = annotation_text
        
        # Look for pattern in annotation
        if "PATTERN:" in annotation_text:
            for line in annotation_text.split("\n"):
                if line.startswith("PATTERN:"):
                    sender.pattern = line.replace("PATTERN:", "").strip()
                    break
        
        self.save_sender_profile(sender)
        self.notify("Notes saved", severity="information")
        
    def action_toggle_done(self) -> None:
        """Not used directly in sender-based view but kept for hotkey compatibility."""
        self.notify("Toggle done not applicable in sender view", severity="information")

    def update_status(self, message: str) -> None:
        """Update the status text in the UI."""
        self.status_text = message 

    def _process_client_results(self, results, col_names):
        """Process client results from the master_clients table.
        
        Args:
            results: Query results from the database
            col_names: Column names for the results
            
        Returns:
            Dict mapping domain names to client information
        """
        logger.debug(f"Processing {len(results)} client records with columns: {col_names}")
        
        # Create lookup for column indices
        col_indices = {name.lower(): idx for idx, name in enumerate(col_names)}
        logger.debug(f"Client table column indices: {col_indices}")
        
        client_data = {}
        
        # Process each client record
        for row in results:
            try:
                # Extract domain information - try multiple possible column names
                domain = None
                if 'domain' in col_indices:
                    domain = row[col_indices['domain']]
                elif 'email_domain' in col_indices:
                    domain = row[col_indices['email_domain']]
                elif 'website' in col_indices:
                    website = row[col_indices['website']]
                    if website:
                        # Extract domain from website URL
                        website = website.replace('http://', '').replace('https://', '')
                        domain = website.split('/')[0] if '/' in website else website
                
                # Extract company/client name
                client_name = None
                if 'name' in col_indices:
                    client_name = row[col_indices['name']]
                elif 'client_name' in col_indices:
                    client_name = row[col_indices['client_name']]
                elif 'company_name' in col_indices:
                    client_name = row[col_indices['company_name']]
                    
                # Skip if no domain
                if not domain:
                    logger.warning(f"Skipping client record - no domain found in row")
                    continue
                    
                # Collect other useful client metadata
                client_info = {
                    'name': client_name or "Unknown Client",
                    'domain': domain
                }
                
                # Add any additional fields that exist
                for field in ['description', 'industry', 'contact_name', 'contact_email', 'phone']:
                    if field in col_indices and row[col_indices[field]]:
                        client_info[field] = row[col_indices[field]]
                
                # Store by domain for easy lookup
                client_data[domain] = client_info
                logger.debug(f"Processed client: {domain} -> {client_name}")
                
            except Exception as e:
                logger.error(f"Error processing client record: {e}")
                logger.debug(traceback.format_exc())
                
        logger.debug(f"Successfully processed {len(client_data)} client records")
        return client_data 