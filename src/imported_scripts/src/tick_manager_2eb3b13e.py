# Standard library
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime

# Third-party
import duckdb
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.pilot import Pilot
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, TextArea

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "logs",
                "tick_manager.log",
            ),
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


class ConnectionState:
    def __init__(self) -> None:
        self.last_success = None
        self.failure_count = 0
        self.last_error = None

    def record_success(self) -> None:
        self.last_success = datetime.now()
        self.failure_count = 0
        self.last_error = None

    def record_failure(self, error) -> None:
        self.failure_count += 1
        self.last_error = error


class PerformanceMetrics:
    def __init__(self) -> None:
        self.api_response_times = []
        self.ui_update_times = []

    def record_api_time(self, duration) -> None:
        self.api_response_times.append(duration)

    def record_ui_time(self, duration) -> None:
        self.ui_update_times.append(duration)

    def get_stats(self):
        return {
            "api_response": {
                "count": len(self.api_response_times),
                "avg": (
                    sum(self.api_response_times) / len(self.api_response_times)
                    if self.api_response_times
                    else 0
                ),
                "max": max(self.api_response_times) if self.api_response_times else 0,
            },
            "ui_update": {
                "count": len(self.ui_update_times),
                "avg": (
                    sum(self.ui_update_times) / len(self.ui_update_times)
                    if self.ui_update_times
                    else 0
                ),
                "max": max(self.ui_update_times) if self.ui_update_times else 0,
            },
        }


def validate_tick_history_data(conn) -> tuple[bool, dict]:
    """Validate tick history data."""
    try:
        # Get total records
        total = conn.execute("SELECT COUNT(*) FROM main.tick_history").fetchone()[0]

        # Check for invalid ticks
        invalid_ticks = conn.execute(
            """
            SELECT COUNT(*) FROM main.tick_history
            WHERE NOT (
                (old_tick IS NULL OR old_tick ~ '^-?[0-9]+$')
                OR old_tick IS NULL
            )
            OR NOT (
                (new_tick IS NULL OR new_tick ~ '^-?[0-9]+$')
                OR new_tick IS NULL
            )
        """,
        ).fetchone()[0]

        # Check for duplicate entries
        duplicates = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT ticker, date, COUNT(*)
                FROM main.tick_history
                GROUP BY ticker, date
                HAVING COUNT(*) > 1
            ) t
        """,
        ).fetchone()[0]

        stats = {
            "total_records": total,
            "invalid_ticks": invalid_ticks,
            "duplicate_entries": duplicates,
        }

        return invalid_ticks == 0 and duplicates == 0, stats

    except Exception as e:
        logger.exception(f"Error validating tick history data: {e}")
        return False, {"error": str(e)}


def cleanup_tick_history(conn) -> bool:
    """Clean up tick history data."""
    try:
        # Remove invalid ticks
        conn.execute(
            """
            DELETE FROM main.tick_history
            WHERE NOT (
                (old_tick IS NULL OR old_tick ~ '^-?[0-9]+$')
                OR old_tick IS NULL
            )
            OR NOT (
                (new_tick IS NULL OR new_tick ~ '^-?[0-9]+$')
                OR new_tick IS NULL
            )
        """,
        )

        # Remove duplicates keeping the latest entry
        conn.execute(
            """
            WITH duplicates AS (
                SELECT ticker, date
                FROM main.tick_history
                GROUP BY ticker, date
                HAVING COUNT(*) > 1
            ),
            latest_entries AS (
                SELECT h.ticker, h.date, h.rowid
                FROM main.tick_history h
                JOIN duplicates d ON h.ticker = d.ticker AND h.date = d.date
                WHERE h.rowid = (
                    SELECT MAX(rowid)
                    FROM main.tick_history h2
                    WHERE h2.ticker = h.ticker AND h2.date = h.date
                )
            )
            DELETE FROM main.tick_history
            WHERE EXISTS (
                SELECT 1
                FROM duplicates d
                WHERE main.tick_history.ticker = d.ticker
                AND main.tick_history.date = d.date
            )
            AND NOT EXISTS (
                SELECT 1
                FROM latest_entries le
                WHERE main.tick_history.ticker = le.ticker
                AND main.tick_history.date = le.date
                AND main.tick_history.rowid = le.rowid
            )
        """,
        )

        return True

    except Exception as e:
        logger.exception(f"Error cleaning up tick history: {e}")
        return False


class TickEditScreen(Screen):
    """Screen for editing tick values."""

    def __init__(
        self,
        ticker: str,
        company_name: str,
        current_tick: str,
        last_note: str,
    ) -> None:
        """Initialize the tick edit screen."""
        super().__init__()
        self.ticker = ticker
        self.company_name = company_name
        self.current_tick = current_tick
        self.last_note = last_note

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Container(
            Label(
                f"Edit Tick for {self.company_name} ({self.ticker})",
                id="edit_title",
            ),
            Label(f"Current Tick: {self.current_tick}", id="current_tick_label"),
            Label("New Tick:", id="new_tick_label"),
            Input(id="new_tick_input", placeholder="Enter new tick value"),
            Label("Note:", id="note_label"),
            TextArea(value=self.last_note, id="note_input"),
            Container(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", variant="default", id="cancel"),
                id="button_container",
            ),
            id="edit_container",
        )

    def validate_tick_value(self, tick: str) -> int:
        """Validate the tick value."""
        try:
            value = int(float(tick))
            if not (-100 <= value <= 100):
                msg = "Tick must be between -100 and 100"
                raise ValueError(msg)
            return value
        except ValueError as e:
            msg = f"Invalid tick value: {e!s}"
            raise ValueError(msg)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "save":
            await self.action_save()

    async def action_save(self) -> None:
        """Save the tick update."""
        if self.connection_status != "connected":
            self.notify("API connection lost", severity="error")
            return

        try:
            new_tick = self.query_one("#new_tick_input").value
            note = self.query_one("#note_input").value

            # Validate inputs
            if not new_tick:
                self.notify("Please enter a new tick value", severity="error")
                return

            new_tick_value = self.validate_tick_value(new_tick)

            # Update via API
            await self.app.api_client.update_tick(
                ticker=self.ticker,
                new_tick=new_tick_value,
                note=note,
            )

            # Refresh the main screen's data
            await self.app.action_refresh()
            self.app.pop_screen()
            self.app.notify("Tick updated successfully")

        except ValueError as e:
            self.notify(str(e), severity="error")
        except Exception as e:
            logger.exception(f"Error saving tick update: {e}")
            self.notify("Error saving tick update", severity="error")


@dataclass
class Notification:
    """A notification message."""

    message: str
    severity: str


class TestScreen(Screen):
    """Test screen for the app."""

    async def wait_for_load(self) -> None:
        """Wait for all UI elements to be mounted."""
        await self.mount()  # Ensure screen is mounted
        await self.query_one("#title").wait_for_mount()
        await self.query_one("#connection_status").wait_for_mount()
        await self.query_one("#companies_table").wait_for_mount()
        await self.query_one("#controls").wait_for_mount()

    def compose(self):
        """Create child widgets for the screen."""
        # Create header
        yield Header(id="header")
        with Container(id="title_container"):
            yield Label("Tick Manager", id="title")
            yield Label("●", id="connection_status", classes="disconnected")

        # Create main content
        with Container(id="main"):
            table = DataTable(id="companies_table")
            table.add_columns("Ticker", "Company", "Tick")
            yield table

            # Create controls
            with Container(id="controls"):
                yield Button("Increase Tick", id="increase_tick", variant="primary")
                yield Button("Decrease Tick", id="decrease_tick", variant="primary")
                yield Button("Edit Tick", id="edit_tick", variant="primary")
                yield Button("Save", id="save", variant="success")
                yield Button("Cancel", id="cancel", variant="error")

        # Create footer
        yield Footer(id="footer")


class TickManagerApp(App):
    """A Textual app to manage company tick sizes."""

    CSS_PATH = "tick_manager.css"
    BINDINGS = [Binding("r", "refresh", "Refresh"), Binding("q", "quit", "Quit")]

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()

        # Use the database path from ethifinx project
        db_path = "/Users/srvo/ethifinx/data/research.duckdb"
        try:
            self.db = duckdb.connect(db_path)
            logger.info(f"Connected to database at {db_path}")

            # Verify/create required schema structure matching alembic migrations
            self.db.execute(
                """
                -- Ensure main schema exists
                CREATE SCHEMA IF NOT EXISTS main;

                -- Create current_universe if it doesn't exist
                CREATE TABLE IF NOT EXISTS main.current_universe (
                    ticker VARCHAR PRIMARY KEY,
                    security_name VARCHAR NOT NULL,
                    tick INTEGER
                );

                -- Create tick_history if it doesn't exist
                CREATE TABLE IF NOT EXISTS main.tick_history (
                    id INTEGER PRIMARY KEY,
                    ticker VARCHAR NOT NULL,
                    old_tick INTEGER,
                    new_tick INTEGER,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    note TEXT,
                    updated_by TEXT
                );

                -- Create or replace view for latest ticks
                CREATE OR REPLACE VIEW main.latest_ticks AS
                SELECT
                    u.ticker,
                    u.security_name,
                    COALESCE(th.new_tick, u.tick) as current_tick,
                    th.date as last_updated,
                    th.note as last_note,
                    th.updated_by
                FROM main.current_universe u
                LEFT JOIN (
                    SELECT DISTINCT ON (ticker)
                        ticker, new_tick, date, note, updated_by
                    FROM main.tick_history
                    ORDER BY ticker, date DESC
                ) th ON u.ticker = th.ticker;
            """,
            )

        except Exception as e:
            logger.exception(f"Failed to connect to database: {e}")
            self.db = None

        self.companies = []
        self.current_company = None
        self.current_tick = None
        self.last_note = None
        self.connection_status = "disconnected"
        self.connection_state = ConnectionState()
        self.performance_metrics = PerformanceMetrics()
        self.connection_check_task = None
        self.notifications = []

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # Create header
        yield Header(id="header")
        with Container(id="title_container"):
            yield Label("Tick Manager", id="title")
            yield Label("●", id="connection_status", classes="disconnected")

        # Create main content
        with Container(id="main"):
            yield DataTable(id="companies_table")

            # Create controls
            with Container(id="controls"):
                yield Button("Increase Tick", id="increase_tick", variant="primary")
                yield Button("Decrease Tick", id="decrease_tick", variant="primary")
                yield Button("Edit Tick", id="edit_tick", variant="primary")
                yield Button("Save", id="save", variant="success")
                yield Button("Cancel", id="cancel", variant="error")

        # Create footer
        yield Footer(id="footer")

    async def run_test(self) -> TickManagerApp:
        """Run the app in test mode."""
        # Initialize API client if not set
        if not self.api_client:
            self.api_client = MockAPIServer()

        # Create and mount the test screen
        screen = TestScreen()
        self._screen_stack.append(screen)  # Push screen first

        # Create a pilot to run the app
        pilot = Pilot(self)
        app = pilot.app  # Get the app instance

        # Mount the screen and wait for it to be ready
        await app.mount()  # Mount the app first
        await screen.mount()  # Then mount the screen
        await screen.wait_for_load()  # Wait for screen to be ready

        # Set initial connection status
        self.connection_status = "connected"
        status_label = screen.query_one("#connection_status")
        status_label.remove_class("disconnected")
        status_label.add_class("connected")

        # Load initial data
        await self.load_companies()

        return app

    def validate_tick_value(self, tick: str) -> int:
        """Validate the tick value."""
        try:
            value = int(float(tick))
            if not (-100 <= value <= 100):
                msg = "Tick must be between -100 and 100"
                raise ValueError(msg)
            return value
        except ValueError as e:
            msg = f"Invalid tick value: {e!s}"
            raise ValueError(msg)

    async def load_companies(self) -> None:
        """Load companies data directly from DuckDB."""
        try:
            # Query using the latest_ticks view
            result = self.db.execute(
                """
                SELECT
                    t.ticker,
                    t.security_name as company,
                    t.current_tick as tick,
                    t.last_updated,
                    t.last_note,
                    t.updated_by
                FROM main.latest_ticks t
                ORDER BY t.ticker;
            """,
            ).fetchall()

            companies = [
                {
                    "ticker": row[0],
                    "company": row[1],
                    "tick": row[2],
                    "last_updated": row[3],
                    "last_note": row[4],
                    "updated_by": row[5],
                }
                for row in result
            ]

            self.companies = companies

            # Update table widget
            table = self.query_one("#companies_table")
            table.clear()

            # Add columns if not already added
            if not table.columns:
                table.add_columns(
                    "Ticker",
                    "Company",
                    "Tick",
                    "Last Updated",
                    "Note",
                    "Updated By",
                )

            # Add rows
            for company in self.companies:
                table.add_row(
                    company["ticker"],
                    company["company"],
                    str(company["tick"] or ""),
                    (
                        company["last_updated"].strftime("%Y-%m-%d %H:%M")
                        if company["last_updated"]
                        else ""
                    ),
                    company["last_note"] or "",
                    company["updated_by"] or "",
                )

        except Exception as e:
            logger.exception(f"Failed to load companies: {e}")
            self.notify("Failed to load companies data", severity="error")

    async def on_mount(self) -> None:
        """Initialize the app when mounted."""
        try:
            # Set initial connection status
            status_label = self.query_one("#connection_status")

            # Test database connection
            if self.db:
                try:
                    # Try to query something simple
                    result = self.db.execute("SELECT 1").fetchone()
                    if result:
                        self.connection_status = "connected"
                        status_label.remove_class("disconnected")
                        status_label.add_class("connected")

                        # Load initial data
                        await self.load_companies()
                except Exception as e:
                    logger.exception(f"Database connection failed: {e}")
                    self.connection_status = "disconnected"
                    status_label.remove_class("connected")
                    status_label.add_class("disconnected")
                    self.notify("Failed to connect to database", severity="error")

        except Exception as e:
            logger.exception(f"Failed to initialize UI: {e}")
            self.connection_status = "disconnected"
            self.notify(f"Initialization error: {e!s}", severity="error")

    async def api_call_with_retry(self, func, *args, max_retries=3, **kwargs):
        """Wrapper for API calls with retry logic."""
        retries = 0
        while retries <= max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                retries += 1
                self.connection_state.failure_count += 1
                self.notify(f"API call failed: {e}", severity="error")
                if retries > max_retries:
                    raise
                await asyncio.sleep(1)  # Wait before retrying
        return None

    def log_error_with_context(self, error, context=None) -> None:
        """Log errors with additional context."""
        error_info = {
            "error": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "connection_state": {
                "last_success": (
                    self.connection_state.last_success.isoformat()
                    if self.connection_state.last_success
                    else None
                ),
                "failure_count": self.connection_state.failure_count,
                "last_error": (
                    str(self.connection_state.last_error)
                    if self.connection_state.last_error
                    else None
                ),
            },
            "performance_metrics": self.performance_metrics.get_stats(),
        }
        logger.error(json.dumps(error_info, indent=2))

    async def check_connection(self) -> None:
        """Periodically check API connection status."""
        while True:
            try:
                start_time = time.time()
                connected = await self.api_call_with_retry(self.api_client.ping)
                duration = time.time() - start_time
                self.performance_metrics.record_api_time(duration)

                if connected:
                    self.connection_status = "connected"
                    self.connection_state.record_success()
                else:
                    self.connection_status = "disconnected"
                    self.connection_state.record_failure("Ping failed")

                self.query_one("#connection_status").set_class(self.connection_status)
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.log_error_with_context(e, {"context": "connection_check"})
                self.connection_status = "disconnected"
                self.query_one("#connection_status").set_class("disconnected")
                await asyncio.sleep(10)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if not self.current_company:
            self.notify("Please select a company first", severity="error")
            return

        try:
            current_tick = int(self.current_company["tick"])

            if event.button.id == "increase_tick":
                new_tick = current_tick + 1
                if await self.update_tick(self.current_company["ticker"], new_tick):
                    await self.load_companies()  # Refresh the display

            elif event.button.id == "decrease_tick":
                new_tick = current_tick - 1
                if await self.update_tick(self.current_company["ticker"], new_tick):
                    await self.load_companies()  # Refresh the display

            elif event.button.id == "edit_tick":
                await self.show_tick_edit_screen(0)  # 0 means no automatic change

        except Exception as e:
            logger.exception(f"Error handling button press: {e}")
            self.notify("Error processing button press", severity="error")

    async def show_tick_edit_screen(self, direction: int) -> None:
        """Show the tick edit screen."""
        try:
            company = await self.api_client.get_company(self.current_company["ticker"])
            current_tick = company["tick"]
            suggested_tick = current_tick + direction

            screen = TickEditScreen(
                ticker=company["ticker"],
                company_name=company["company"],
                current_tick=str(current_tick),
                last_note=company.get("last_note", ""),
            )
            self.push_screen(screen)
            screen.query_one("#new_tick_input").value = str(suggested_tick)

        except Exception as e:
            logger.exception(f"Error showing tick edit screen: {e}")
            self.notify("Error showing edit screen", severity="error")

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the companies table."""
        try:
            table = event.data_table
            if table.cursor_row is None:
                self.current_company = None
                await self.update_current_tick_display()
                return

            row_data = table.get_row_at(table.cursor_row)
            if not row_data or len(row_data) < 3:
                msg = "Invalid row data"
                raise ValueError(msg)

            # Get full company details from API
            company = await self.api_client.get_company(row_data[0])
            self.current_company = company
            await self.update_current_tick_display()

        except Exception as e:
            logger.exception(f"Error handling row selection: {e}")
            self.current_company = None
            await self.update_current_tick_display()
            self.notify("Error selecting company", severity="error")

    async def update_current_tick_display(self) -> None:
        """Update the current tick display."""
        if self.current_company:
            tick = str(self.current_company["tick"])
            self.query_one("#current_tick_display").update(tick)
        else:
            self.query_one("#current_tick_display").update("0")

    async def initialize_ui(self) -> None:
        """Initialize the UI components."""
        try:
            # Load companies from API
            companies_data = await self.api_client.get_companies()
            self.companies = companies_data["items"]

            # Set up data table
            table = self.query_one(DataTable)
            table.add_column("Ticker", key="ticker")
            table.add_column("Company", key="company")
            table.add_column("Tick", key="tick")

            # Add companies to table
            for company in self.companies:
                table.add_row(
                    company["ticker"],
                    company["company"],
                    str(company["tick"]),
                )

        except Exception as e:
            logger.exception(f"Failed to initialize UI: {e}")
            self.notify("Failed to load companies data", severity="error")

    async def on_unmount(self) -> None:
        """Clean up resources when the app is closing."""
        if self.connection_check_task:
            self.connection_check_task.cancel()
        if self.db:
            self.db.close()

    async def action_refresh(self) -> None:
        """Refresh the companies data."""
        try:
            await self.api_call_with_retry(self.load_companies)
        except Exception as e:
            self.log.exception(f"Failed to refresh data: {e}")
            self.notify("Failed to refresh data", severity="error")

    async def click(self, widget_type) -> None:
        """Simulate a click on a widget type."""
        widget = self.query_one(widget_type)
        await self.on_data_table_row_selected(widget)

    async def press(self, key) -> None:
        """Simulate a key press."""
        if key == "r":
            await self.action_refresh()
        elif key == "down":
            table = self.query_one(DataTable)
            if table.cursor_row is None:
                table.cursor_row = 0
            else:
                table.cursor_row += 1
            await self.on_data_table_row_selected(table)

    def notify(self, message: str, severity: str = "info") -> None:
        """Add a notification message."""
        self.notifications.append(Notification(message=message, severity=severity))
        super().notify(message, severity=severity)

    async def refresh_data(self) -> None:
        """Refresh the companies data."""
        try:
            await self.api_call_with_retry(self.load_companies)
        except Exception as e:
            self.log.exception(f"Failed to refresh data: {e}")
            self.notify("Failed to refresh data", severity="error")

    async def update_tick(
        self,
        ticker: str,
        new_tick: int,
        note: str | None = None,
    ) -> bool:
        """Update the tick value for a company."""
        try:
            # Get current tick from latest_ticks view
            current = self.db.execute(
                """
                SELECT current_tick
                FROM main.latest_ticks
                WHERE ticker = ?
            """,
                [ticker],
            ).fetchone()

            old_tick = current[0] if current else None

            # Insert new tick history record
            self.db.execute(
                """
                INSERT INTO main.tick_history (
                    ticker,
                    old_tick,
                    new_tick,
                    date,
                    note,
                    updated_by
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, 'TUI')
            """,
                [ticker, old_tick, new_tick, note],
            )

            # Update current_universe table
            self.db.execute(
                """
                UPDATE main.current_universe
                SET tick = ?
                WHERE ticker = ?
            """,
                [new_tick, ticker],
            )

            return True

        except Exception as e:
            logger.exception(f"Failed to update tick: {e}")
            self.notify(f"Failed to update tick: {e!s}", severity="error")
            return False


class MockAPIServer:
    """Mock API server for testing."""

    def __init__(self) -> None:
        self.companies = [
            {"ticker": "AAPL", "company": "Apple Inc.", "tick": 1},
            {"ticker": "MSFT", "company": "Microsoft Corp.", "tick": 2},
            {"ticker": "GOOGL", "company": "Alphabet Inc.", "tick": 3},
        ]
        self.ping_result = True

    async def ping(self):
        return self.ping_result

    async def get_companies(self):
        return self.companies

    async def update_tick(self, ticker, new_tick, note=None) -> bool:
        for company in self.companies:
            if company["ticker"] == ticker:
                company["tick"] = new_tick
                return True
        return False


if __name__ == "__main__":
    app = TickManagerApp()
    app.run()
