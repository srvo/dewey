#!/usr/bin/env python3
"""
Feedback Manager TUI

A Textual-based Terminal User Interface for managing feedback,
flagging follow-ups, and annotating contacts, using PostgreSQL.
"""

import datetime
import logging
from typing import Any

# Import database utilities for PostgreSQL
from dewey.utils.database import (
    create_table_if_not_exists,
    execute_query,
    fetch_all,
    initialize_pool,
)
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)

logger = logging.getLogger(__name__)


class FeedbackItem:
    """Represents a feedback item with all necessary properties."""

    def __init__(
        self,
        msg_id: str,
        subject: str,
        original_priority: int,
        assigned_priority: int,
        suggested_priority: int | None,
        feedback_comments: str | None,
        add_to_topics: str | None,
        timestamp: datetime.datetime,
        follow_up: bool = False,
        contact_email: str | None = None,
        contact_name: str | None = None,
        contact_notes: str | None = None,
    ):
        self.msg_id = msg_id
        self.subject = subject
        self.original_priority = original_priority
        self.assigned_priority = assigned_priority
        self.suggested_priority = suggested_priority
        self.feedback_comments = feedback_comments
        self.add_to_topics = add_to_topics
        self.timestamp = timestamp
        self.follow_up = follow_up
        self.contact_email = contact_email
        self.contact_name = contact_name
        self.contact_notes = contact_notes

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackItem":
        """Create a FeedbackItem from a dictionary."""
        return cls(
            msg_id=data.get("msg_id", ""),
            subject=data.get("subject", ""),
            original_priority=data.get("original_priority", 0),
            assigned_priority=data.get("assigned_priority", 0),
            suggested_priority=data.get("suggested_priority"),
            feedback_comments=data.get("feedback_comments", ""),
            add_to_topics=data.get("add_to_topics", ""),
            timestamp=data.get("timestamp", datetime.datetime.now()),
            follow_up=data.get("follow_up", False),
            contact_email=data.get("contact_email"),
            contact_name=data.get("contact_name"),
            contact_notes=data.get("contact_notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "msg_id": self.msg_id,
            "subject": self.subject,
            "original_priority": self.original_priority,
            "assigned_priority": self.assigned_priority,
            "suggested_priority": self.suggested_priority,
            "feedback_comments": self.feedback_comments,
            "add_to_topics": self.add_to_topics,
            "timestamp": self.timestamp,
            "follow_up": self.follow_up,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "contact_notes": self.contact_notes,
        }


class FeedbackDatabase:
    """Database manager for feedback data using PostgreSQL."""

    def __init__(self):
        initialize_pool()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure required tables exist in the PostgreSQL database."""
        feedback_table = "feedback"
        columns_definition = (
            "msg_id VARCHAR(255) PRIMARY KEY, "
            "subject TEXT, "
            "original_priority INTEGER, "
            "assigned_priority INTEGER, "
            "suggested_priority INTEGER, "
            "feedback_comments TEXT, "
            "add_to_topics TEXT, "
            "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
            "follow_up BOOLEAN DEFAULT FALSE, "
            "contact_email VARCHAR(255), "
            "contact_name TEXT, "
            "contact_notes TEXT"
        )
        try:
            create_table_if_not_exists(feedback_table, columns_definition)
            logger.debug(f"Ensured table '{feedback_table}' exists.")

            index_name = "idx_feedback_follow_up"
            index_query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {feedback_table}(follow_up);"
            execute_query(index_query)
            logger.debug(f"Ensured index '{index_name}' exists.")

        except Exception as e:
            logger.error(f"Error ensuring tables/indexes: {e}")
            raise

    def get_all_feedback(self) -> list[FeedbackItem]:
        """Get all feedback items from the database."""
        query = "SELECT * FROM feedback ORDER BY timestamp DESC"
        try:
            results = fetch_all(query)
            colnames = self._get_table_columns("feedback")
            if not colnames:
                logger.error("Could not retrieve column names for feedback table.")
                return []

            feedback_items = []
            for row in results:
                item_dict = dict(zip(colnames, row, strict=False))
                feedback_items.append(FeedbackItem.from_dict(item_dict))
            return feedback_items
        except Exception as e:
            logger.error(f"Error getting all feedback: {e}")
            return []

    def get_follow_up_items(self) -> list[FeedbackItem]:
        """Get all feedback items flagged for follow-up."""
        query = "SELECT * FROM feedback WHERE follow_up = TRUE ORDER BY timestamp DESC"
        try:
            results = fetch_all(query)
            colnames = self._get_table_columns("feedback")
            if not colnames:
                logger.error("Could not retrieve column names for feedback table.")
                return []

            feedback_items = []
            for row in results:
                item_dict = dict(zip(colnames, row, strict=False))
                feedback_items.append(FeedbackItem.from_dict(item_dict))
            return feedback_items
        except Exception as e:
            logger.error(f"Error getting follow-up items: {e}")
            return []

    def _get_table_columns(
        self, table_name: str, schema: str = "public",
    ) -> list[str] | None:
        """Helper to get column names for a table."""
        query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        try:
            results = fetch_all(query, [schema, table_name])
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting columns for table {schema}.{table_name}: {e}")
            return None

    def add_or_update_feedback(self, feedback_item: FeedbackItem) -> None:
        """Add or update a feedback item using PostgreSQL's ON CONFLICT."""
        query = """
        INSERT INTO feedback (
            msg_id, subject, original_priority, assigned_priority, suggested_priority,
            feedback_comments, add_to_topics, timestamp, follow_up,
            contact_email, contact_name, contact_notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (msg_id) DO UPDATE SET
            subject = EXCLUDED.subject,
            original_priority = EXCLUDED.original_priority,
            assigned_priority = EXCLUDED.assigned_priority,
            suggested_priority = EXCLUDED.suggested_priority,
            feedback_comments = EXCLUDED.feedback_comments,
            add_to_topics = EXCLUDED.add_to_topics,
            timestamp = EXCLUDED.timestamp,
            follow_up = EXCLUDED.follow_up,
            contact_email = EXCLUDED.contact_email,
            contact_name = EXCLUDED.contact_name,
            contact_notes = EXCLUDED.contact_notes
        """
        params = [
            feedback_item.msg_id,
            feedback_item.subject,
            feedback_item.original_priority,
            feedback_item.assigned_priority,
            feedback_item.suggested_priority,
            feedback_item.feedback_comments,
            feedback_item.add_to_topics,
            feedback_item.timestamp,
            feedback_item.follow_up,
            feedback_item.contact_email,
            feedback_item.contact_name,
            feedback_item.contact_notes,
        ]
        try:
            execute_query(query, params)
            logger.debug(f"Upserted feedback item: {feedback_item.msg_id}")
        except Exception as e:
            logger.error(f"Error upserting feedback item {feedback_item.msg_id}: {e}")
            # Decide if re-raise is needed

    def delete_feedback(self, msg_id: str) -> None:
        """Delete a feedback item from the database."""
        query = "DELETE FROM feedback WHERE msg_id = %s"
        params = [msg_id]
        try:
            execute_query(query, params)
            logger.debug(f"Deleted feedback item: {msg_id}")
        except Exception as e:
            logger.error(f"Error deleting feedback item {msg_id}: {e}")
            # Decide if re-raise is needed

    def toggle_follow_up(self, msg_id: str, follow_up: bool) -> None:
        """Toggle the follow-up flag for a feedback item."""
        query = "UPDATE feedback SET follow_up = %s WHERE msg_id = %s"
        params = [follow_up, msg_id]
        try:
            execute_query(query, params)
            logger.debug(f"Toggled follow-up for feedback item: {msg_id}")
        except Exception as e:
            logger.error(f"Error toggling follow-up for feedback item {msg_id}: {e}")
            # Decide if re-raise is needed

    def update_contact_notes(self, email: str, notes: str) -> None:
        """Update notes for a contact."""
        if not email:
            return

        query = "UPDATE feedback SET contact_notes = %s WHERE contact_email = %s"
        params = [notes, email]
        try:
            execute_query(query, params)
            logger.debug(f"Updated contact notes for: {email}")
        except Exception as e:
            logger.error(f"Error updating contact notes for {email}: {e}")
            # Decide if re-raise is needed

    def get_email_threads(
        self, contact_email: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get email threads from MotherDuck, optionally filtered by contact."""
        if not self.md_conn:
            return []

        try:
            md_conn = duckdb.connect(self.md_conn)

            query = """
                SELECT
                    thread_id,
                    client_email,
                    subject,
                    client_message,
                    response_message,
                    actual_received_time,
                    actual_response_time
                FROM client_communications_index
            """

            params = []
            if contact_email:
                query += " WHERE client_email = ?"
                params.append(contact_email)

            query += " ORDER BY actual_received_time DESC LIMIT 50"

            result = md_conn.execute(query, params).fetchall()
            columns = [col[0] for col in md_conn.description()]

            md_conn.close()

            threads = []
            for row in result:
                thread_dict = dict(zip(columns, row, strict=False))
                threads.append(thread_dict)

            return threads

        except Exception as e:
            print(f"Error fetching email threads: {e}")
            return []


class ContactDetailModal(ModalScreen):
    """Modal for viewing and editing contact details."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, contact_email: str, contact_name: str, contact_notes: str):
        super().__init__()
        self.contact_email = contact_email
        self.contact_name = contact_name
        self.contact_notes = contact_notes
        self.db = FeedbackDatabase()
        self.communication_threads = []

    def compose(self) -> ComposeResult:
        with Container(id="contact-modal"):
            yield Header(f"Contact Details: {self.contact_name or self.contact_email}")

            with Vertical(id="contact-details"):
                yield Label("Email:")
                yield Input(value=self.contact_email, id="contact-email")
                yield Label("Name:")
                yield Input(value=self.contact_name or "", id="contact-name")
                yield Label("Notes:")
                yield TextArea(value=self.contact_notes or "", id="contact-notes")

                yield Label("Communication History:", classes="section-header")
                yield DataTable(id="communication-table")

            with Horizontal(id="button-container"):
                yield Button("Cancel", variant="error", id="cancel-button")
                yield Button("Save", variant="success", id="save-button")

    def on_mount(self) -> None:
        """Load communication history when the modal is mounted."""
        self.load_communication_history()

    @work
    async def load_communication_history(self) -> None:
        """Load communication history for this contact."""
        threads = self.db.get_email_threads(self.contact_email)
        self.communication_threads = threads

        # Populate the data table
        table = self.query_one("#communication-table", DataTable)
        table.add_columns("Date", "Subject", "Client Message", "Response")

        for thread in threads:
            received_time = thread.get("actual_received_time")
            date_str = (
                received_time.strftime("%Y-%m-%d %H:%M") if received_time else "Unknown"
            )

            subject = thread.get("subject", "")
            client_msg = thread.get("client_message", "")
            if len(client_msg) > 50:
                client_msg = client_msg[:47] + "..."

            response = thread.get("response_message", "")
            if len(response) > 50:
                response = response[:47] + "..."

            table.add_row(date_str, subject, client_msg, response)

    @on(Button.Pressed, "#cancel-button")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.dismiss()

    @on(Button.Pressed, "#save-button")
    def handle_save(self) -> None:
        """Handle save button press."""
        email = self.query_one("#contact-email", Input).value
        name = self.query_one("#contact-name", Input).value
        notes = self.query_one("#contact-notes", TextArea).value

        # Update the contact notes in the database
        self.db.update_contact_notes(email, notes)

        # Return the updated values to the caller
        self.dismiss((email, name, notes))


class FeedbackEditModal(ModalScreen):
    """Modal for editing feedback details."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, feedback_item: FeedbackItem):
        super().__init__()
        self.feedback_item = feedback_item

    def compose(self) -> ComposeResult:
        with Container(id="feedback-modal"):
            yield Header(f"Edit Feedback: {self.feedback_item.subject}")

            with Vertical(id="feedback-details"):
                yield Label("Subject:")
                yield Input(
                    value=self.feedback_item.subject, id="subject-input", disabled=True,
                )

                yield Label("Original Priority:")
                yield Input(
                    value=str(self.feedback_item.original_priority),
                    id="orig-priority-input",
                    disabled=True,
                )

                yield Label("Assigned Priority:")
                yield Select(
                    [(str(i), str(i)) for i in range(5)],
                    value=str(self.feedback_item.assigned_priority),
                    id="assigned-priority-select",
                )

                yield Label("Suggested Priority:")
                yield Select(
                    [(str(i), str(i)) for i in range(5)] + [("None", "")],
                    value=str(self.feedback_item.suggested_priority)
                    if self.feedback_item.suggested_priority is not None
                    else "",
                    id="suggested-priority-select",
                )

                yield Label("Feedback Comments:")
                yield TextArea(
                    value=self.feedback_item.feedback_comments or "",
                    id="feedback-comments",
                )

                yield Label("Topics (comma separated):")
                yield Input(
                    value=self.feedback_item.add_to_topics or "", id="topics-input",
                )

                yield Checkbox(
                    "Flag for Follow-up",
                    value=self.feedback_item.follow_up,
                    id="follow-up-checkbox",
                )

            with Horizontal(id="button-container"):
                yield Button("Cancel", variant="error", id="cancel-button")
                yield Button("Save", variant="success", id="save-button")

    @on(Button.Pressed, "#cancel-button")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.dismiss()

    @on(Button.Pressed, "#save-button")
    def handle_save(self) -> None:
        """Handle save button press."""
        # Update feedback item with new values
        self.feedback_item.subject = self.query_one("#subject-input", Input).value

        assigned_priority = self.query_one("#assigned-priority-select", Select).value
        self.feedback_item.assigned_priority = (
            int(assigned_priority) if assigned_priority else 0
        )

        suggested_priority = self.query_one("#suggested-priority-select", Select).value
        self.feedback_item.suggested_priority = (
            int(suggested_priority) if suggested_priority else None
        )

        self.feedback_item.feedback_comments = self.query_one(
            "#feedback-comments", TextArea,
        ).value
        self.feedback_item.add_to_topics = self.query_one("#topics-input", Input).value
        self.feedback_item.follow_up = self.query_one(
            "#follow-up-checkbox", Checkbox,
        ).value

        # Return the updated feedback item to the caller
        self.dismiss(self.feedback_item)


class FeedbackManagerApp(App):
    """Main application for managing feedback."""

    TITLE = "Dewey Feedback Manager"
    CSS_PATH = "feedback_manager.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "add_feedback", "Add Feedback"),
        Binding("f", "filter_followups", "Toggle Follow-ups"),
        Binding("d", "delete_feedback", "Delete"),
        Binding("e", "edit_feedback", "Edit"),
        Binding("c", "view_contact", "Contact Details"),
        Binding("/", "search", "Search"),
        Binding("?", "help", "Help"),
    ]

    show_follow_ups_only = reactive(False)
    search_query = reactive("")
    selected_index = reactive(-1)

    def __init__(self):
        super().__init__()
        self.db = FeedbackDatabase()
        self.feedback_items = []
        self.filtered_items = []

    def compose(self) -> ComposeResult:
        """Compose the interface."""
        yield Header()

        with Container(id="main-container"):
            yield Static(id="status-bar")
            yield Input(placeholder="Search feedbacks...", id="search-input")
            yield DataTable(id="feedback-table")

            with Container(id="detail-container"):
                yield Static(
                    "Select a feedback item to view details", id="detail-header",
                )
                with Vertical(id="feedback-details"):
                    yield Static("", id="feedback-subject")
                    yield Static("", id="feedback-metadata")
                    yield Static("", id="feedback-comments")

                with Vertical(id="contact-details"):
                    yield Static("", id="contact-header")
                    yield Static("", id="contact-info")
                    yield Static("", id="contact-notes")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the interface when the app is mounted."""
        self.setup_table()
        self.load_feedback_data()

    def setup_table(self) -> None:
        """Set up the feedback data table."""
        table = self.query_one("#feedback-table", DataTable)
        table.add_columns(
            "ID",
            "Subject",
            "Priority",
            "Suggested",
            "Topics",
            "Follow Up",
            "Date",
            "Contact",
        )
        table.cursor_type = "row"

    @work
    async def load_feedback_data(self) -> None:
        """Load feedback data from the database."""
        # Show loading indicator
        self.query_one("#status-bar", Static).update("Loading feedback data...")

        # Get feedback data
        if self.show_follow_ups_only:
            self.feedback_items = self.db.get_follow_up_items()
        else:
            self.feedback_items = self.db.get_all_feedback()

        # Apply search filter if present
        self.apply_filters()

        # Update status bar
        total = len(self.feedback_items)
        shown = len(self.filtered_items)
        follow_ups = sum(1 for item in self.feedback_items if item.follow_up)

        status = f"Showing {shown} of {total} feedback items ({follow_ups} flagged for follow-up)"
        if self.show_follow_ups_only:
            status += " | Follow-ups only"

        self.query_one("#status-bar", Static).update(status)

    def apply_filters(self) -> None:
        """Apply filters to the feedback data."""
        # Apply search filter
        if self.search_query:
            query = self.search_query.lower()
            self.filtered_items = [
                item
                for item in self.feedback_items
                if (
                    query in item.subject.lower()
                    or query in (item.feedback_comments or "").lower()
                    or query in (item.add_to_topics or "").lower()
                    or query in (item.contact_email or "").lower()
                    or query in (item.contact_name or "").lower()
                )
            ]
        else:
            self.filtered_items = self.feedback_items

        # Update table
        self.update_table()

    def update_table(self) -> None:
        """Update the feedback table with current data."""
        table = self.query_one("#feedback-table", DataTable)
        table.clear()

        for item in self.filtered_items:
            # Format data for display
            short_id = item.msg_id[:8] + "..."

            subject = item.subject
            if len(subject) > 40:
                subject = subject[:37] + "..."

            priority = str(item.assigned_priority)
            suggested = (
                str(item.suggested_priority)
                if item.suggested_priority is not None
                else "-"
            )

            topics = item.add_to_topics or "-"
            if len(topics) > 20:
                topics = topics[:17] + "..."

            follow_up = "✓" if item.follow_up else ""

            date = item.timestamp.strftime("%Y-%m-%d %H:%M") if item.timestamp else "-"

            contact = item.contact_name or item.contact_email or "-"
            if len(contact) > 20:
                contact = contact[:17] + "..."

            table.add_row(
                short_id, subject, priority, suggested, topics, follow_up, date, contact,
            )

        # Reset selection
        if table.row_count > 0:
            table.cursor_coordinates = (0, 0)
            self.selected_index = 0
            self.update_detail_view()
        else:
            self.selected_index = -1
            self.clear_detail_view()

    def update_detail_view(self) -> None:
        """Update the detail view with the selected item."""
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_items):
            self.clear_detail_view()
            return

        item = self.filtered_items[self.selected_index]

        # Update feedback details
        self.query_one("#detail-header", Static).update("Feedback Details")
        self.query_one("#feedback-subject", Static).update(f"Subject: {item.subject}")

        metadata = (
            f"Priority: {item.assigned_priority} "
            f"(Original: {item.original_priority}, Suggested: {item.suggested_priority or 'None'})\n"
            f"Date: {item.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            f"Follow-up: {'Yes' if item.follow_up else 'No'}\n"
            f"Topics: {item.add_to_topics or 'None'}"
        )
        self.query_one("#feedback-metadata", Static).update(metadata)

        comments = item.feedback_comments or "No comments"
        self.query_one("#feedback-comments", Static).update(f"Comments:\n{comments}")

        # Update contact details
        if item.contact_email or item.contact_name:
            contact = item.contact_name or ""
            if item.contact_email:
                if contact:
                    contact += f" ({item.contact_email})"
                else:
                    contact = item.contact_email

            self.query_one("#contact-header", Static).update("Contact Information")
            self.query_one("#contact-info", Static).update(contact)

            notes = item.contact_notes or "No notes"
            self.query_one("#contact-notes", Static).update(f"Notes:\n{notes}")
        else:
            self.query_one("#contact-header", Static).update("")
            self.query_one("#contact-info", Static).update("")
            self.query_one("#contact-notes", Static).update("")

    def clear_detail_view(self) -> None:
        """Clear the detail view."""
        self.query_one("#detail-header", Static).update(
            "Select a feedback item to view details",
        )
        self.query_one("#feedback-subject", Static).update("")
        self.query_one("#feedback-metadata", Static).update("")
        self.query_one("#feedback-comments", Static).update("")
        self.query_one("#contact-header", Static).update("")
        self.query_one("#contact-info", Static).update("")
        self.query_one("#contact-notes", Static).update("")

    @on(DataTable.CellSelected)
    def handle_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection in the feedback table."""
        self.selected_index = event.coordinate.row
        self.update_detail_view()

    @on(Input.Changed, "#search-input")
    def handle_search_input(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        self.search_query = event.value
        self.apply_filters()

    async def action_add_feedback(self) -> None:
        """Add a new feedback item."""
        self.notify("This feature is not yet implemented", title="Coming Soon")

    async def action_edit_feedback(self) -> None:
        """Edit the selected feedback item."""
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_items):
            self.notify("Please select a feedback item first", title="No Selection")
            return

        item = self.filtered_items[self.selected_index]
        result = await self.push_screen(FeedbackEditModal(item), wait=True)

        if result:
            # Update the item in the database
            self.db.add_or_update_feedback(result)

            # Refresh the data
            await self.load_feedback_data()

            self.notify("Feedback updated successfully", title="Success")

    async def action_view_contact(self) -> None:
        """View and edit contact details."""
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_items):
            self.notify("Please select a feedback item first", title="No Selection")
            return

        item = self.filtered_items[self.selected_index]

        if not item.contact_email:
            self.notify(
                "No contact email associated with this feedback", title="No Contact",
            )
            return

        result = await self.push_screen(
            ContactDetailModal(
                item.contact_email, item.contact_name, item.contact_notes,
            ),
            wait=True,
        )

        if result:
            email, name, notes = result

            # Update the contact info for this feedback item
            item.contact_email = email
            item.contact_name = name
            item.contact_notes = notes

            # Update the database
            self.db.add_or_update_feedback(item)

            # Refresh the data
            await self.load_feedback_data()

            self.notify("Contact updated successfully", title="Success")

    async def action_delete_feedback(self) -> None:
        """Delete the selected feedback item."""
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_items):
            self.notify("Please select a feedback item first", title="No Selection")
            return

        item = self.filtered_items[self.selected_index]

        # Ask for confirmation
        confirmation = (
            f"Are you sure you want to delete the feedback for '{item.subject}'?"
        )
        if await self.confirm(confirmation, title="Confirm Delete"):
            # Delete the item
            self.db.delete_feedback(item.msg_id)

            # Refresh the data
            await self.load_feedback_data()

            self.notify("Feedback deleted successfully", title="Success")

    async def action_filter_followups(self) -> None:
        """Toggle showing only follow-up items."""
        self.show_follow_ups_only = not self.show_follow_ups_only
        await self.load_feedback_data()

    async def action_refresh(self) -> None:
        """Refresh the feedback data."""
        await self.load_feedback_data()
        self.notify("Data refreshed", title="Refresh")

    def action_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    async def action_help(self) -> None:
        """Show help information."""
        help_text = """
        Feedback Manager Help

        Keyboard Shortcuts:
        - r: Refresh data
        - a: Add new feedback
        - e: Edit selected feedback
        - d: Delete selected feedback
        - f: Toggle follow-up filter
        - c: View/edit contact details
        - /: Search
        - ?: Show this help
        - q: Quit

        Tips:
        - Select a row to view details
        - Flag items for follow-up with the checkbox
        - Add notes to contacts for future reference
        """

        self.notify(help_text, title="Help")


def create_css_file() -> None:
    """Create the CSS file for styling the application."""
    css_content = """
    /* Feedback Manager TUI Stylesheet */

    Screen {
        background: $surface;
        color: $text;
    }

    #main-container {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1 1fr 1fr;
        height: 100%;
        width: 100%;
    }

    #status-bar {
        background: $primary-background;
        color: $text;
        padding: 1 2;
        width: 100%;
        height: 3;
        content-align: center middle;
    }

    #search-input {
        margin: 1 1;
    }

    #feedback-table {
        min-height: 10;
        height: 100%;
        border: solid $primary;
        margin: 0 1;
    }

    #detail-container {
        height: 100%;
        padding: 1;
        border: solid $primary;
        margin: 0 1;
    }

    #detail-header {
        background: $primary-darken-2;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    #feedback-details {
        margin: 1 0;
    }

    #contact-details {
        margin: 1 0;
        border-top: solid $primary;
        padding-top: 1;
    }

    #feedback-subject, #contact-header {
        text-style: bold;
        color: $secondary;
    }

    #feedback-metadata, #contact-info {
        color: $text-muted;
    }

    /* Modal styling */

    #feedback-modal, #contact-modal {
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        margin: 2 4;
        height: auto;
        min-width: 40;
        max-width: 90%;
        min-height: 20;
        max-height: 90%;
    }

    #button-container {
        content-align: center middle;
        width: 100%;
        height: auto;
        margin-top: 2;
    }

    Button {
        margin: 0 1;
    }

    TextArea {
        min-height: 5;
        margin: 1 0;
    }

    #communication-table {
        margin: 1 0;
        height: auto;
        min-height: 5;
        max-height: 10;
    }
    """

    with open("src/ui/feedback_manager.tcss", "w") as f:
        f.write(css_content)


# Create CSS file if running this module directly
if __name__ == "__main__":
    create_css_file()
    app = FeedbackManagerApp()
    app.run()
