import logging
import os
import sys

import duckdb
from alembic import command
from alembic.config import Config

# Constants for database and logging configuration
DB_PATH = "/Users/srvo/local/data/ecic.duckdb"  # Path to DuckDB database file
LOG_DIR = "/Users/srvo/local/logs"  # Directory for log files
LOG_FILE = os.path.join(LOG_DIR, "cli_tick_manager.log")  # Path to log file

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Log to file
        logging.StreamHandler(),  # Log to console
    ],
)
logger = logging.getLogger(__name__)  # Create logger instance


def run_migrations() -> None:
    """Run Alembic migrations to ensure database schema is up-to-date.

    Raises
    ------
        Exception: If migrations fail to run

    """
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"duckdb:///{DB_PATH}")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as e:
        logger.exception(f"Error running migrations: {e}")
        raise


class CLITickManager:
    """Command-line interface for managing company tick values.

    Attributes
    ----------
        conn (duckdb.DuckDBPyConnection): Database connection instance

    """

    def __init__(self) -> None:
        """Initialize the CLI manager and database connection.

        Raises
        ------
            Exception: If database setup or schema validation fails

        """
        self.conn = None
        try:
            # Setup database first
            self.setup_database()
            self.validate_schema()
        except Exception as e:
            logger.exception(f"Failed to initialize CLI manager: {e}")
            raise

    def setup_database(self) -> None:
        """Set up and verify the database connection and required tables.

        Raises
        ------
            RuntimeError: If required tables are missing after migrations
            Exception: If database connection fails

        """
        try:
            self.conn = duckdb.connect(DB_PATH)
            logger.info(f"Connected to DuckDB at {DB_PATH}")

            # Verify required tables exist
            required_tables = {"current_universe", "tick_history"}
            existing_tables = {
                row[0] for row in self.conn.execute("SHOW TABLES").fetchall()
            }

            if not required_tables.issubset(existing_tables):
                missing = required_tables - existing_tables
                logger.warning(f"Missing tables: {missing}. Running migrations...")
                self.run_migrations()

                # Verify again after migrations
                existing_tables = {
                    row[0] for row in self.conn.execute("SHOW TABLES").fetchall()
                }
                if not required_tables.issubset(existing_tables):
                    error_msg = f"Failed to create required tables: {missing}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

        except Exception as e:
            logger.exception(f"Failed to setup database: {e}")
            raise

    def validate_schema(self) -> None:
        """Validate the database schema against required table structure.

        Verifies that required tables and columns exist in the database.

        Raises
        ------
            ValueError: If required tables or columns are missing
            Exception: If schema validation fails

        """
        try:
            # Check current_universe table
            current_universe_cols = {
                row[0]
                for row in self.conn.execute(
                    "PRAGMA table_info(current_universe)",
                ).fetchall()
            }
            required_current_universe = {"ticker", "security_name", "tick"}
            if not required_current_universe.issubset(current_universe_cols):
                missing = required_current_universe - current_universe_cols
                msg = f"current_universe missing columns: {missing}"
                raise ValueError(msg)

            # Check tick_history table
            tick_history_cols = {
                row[0]
                for row in self.conn.execute(
                    "PRAGMA table_info(tick_history)",
                ).fetchall()
            }
            required_tick_history = {"ticker", "old_tick", "new_tick", "date", "note"}
            if not required_tick_history.issubset(tick_history_cols):
                missing = required_tick_history - tick_history_cols
                msg = f"tick_history missing columns: {missing}"
                raise ValueError(msg)

            logger.info("Database schema validated successfully")
        except Exception as e:
            logger.exception(f"Schema validation failed: {e}")
            raise

    def validate_tick_value(self, tick: str) -> int:
        """Validate and convert tick value string to integer.

        Args:
        ----
            tick (str): The tick value as a string

        Returns:
        -------
            int: Validated tick value as integer

        Raises:
        ------
            ValueError: If tick value is invalid or out of range

        """
        try:
            tick_value = int(tick)
            if not (-100 <= tick_value <= 100):
                msg = "Tick value must be between -100 and 100"
                raise ValueError(msg)
            return tick_value
        except ValueError as e:
            logger.exception(f"Invalid tick value: {tick} - {e!s}")
            raise

    def get_top_companies(self, limit: int = 50) -> list[tuple[str, str, int]]:
        """Get top companies sorted by their tick rating.

        Args:
        ----
            limit (int): Maximum number of companies to return

        Returns:
        -------
            List[Tuple[str, str, int]]: List of (ticker, name, tick) tuples

        Raises:
        ------
            Exception: If database query fails

        """
        try:
            return self.conn.execute(
                """
                SELECT ticker, security_name, tick
                FROM current_universe
                ORDER BY tick DESC
                LIMIT ?
            """,
                [limit],
            ).fetchall()
        except Exception as e:
            logger.exception(f"Error getting top companies: {e}")
            raise

    def update_tick_value(self, ticker: str, new_tick: str, note: str) -> None:
        """Update a company's tick value and record the change in history.

        Args:
        ----
            ticker (str): Company ticker symbol
            new_tick (str): New tick value as string
            note (str): Description of the change

        Raises:
        ------
            ValueError: If inputs are invalid or ticker not found
            Exception: If database update fails

        """
        try:
            # Validate inputs
            if not ticker or not isinstance(ticker, str):
                msg = "Invalid ticker"
                raise ValueError(msg)
            if not note or not isinstance(note, str):
                msg = "Invalid note"
                raise ValueError(msg)

            new_tick_value = self.validate_tick_value(new_tick)

            # Get current tick value
            current_tick = self.conn.execute(
                """
                SELECT tick
                FROM current_universe
                WHERE ticker = ?
            """,
                [ticker],
            ).fetchone()

            if not current_tick:
                msg = f"Ticker {ticker} not found in database"
                raise ValueError(msg)

            old_tick = (
                str(current_tick[0])
                if current_tick and current_tick[0] is not None
                else "0"
            )
            old_tick_value = self.validate_tick_value(old_tick)

            # Execute updates within a transaction
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE current_universe
                    SET tick = ?
                    WHERE ticker = ?
                """,
                    [new_tick_value, ticker],
                )

                cursor.execute(
                    """
                    INSERT INTO tick_history (ticker, old_tick, new_tick, note, date)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    [ticker, old_tick_value, new_tick_value, note],
                )

            logger.info(f"Successfully updated tick for {ticker} to {new_tick_value}")

        except Exception as e:
            logger.exception(f"Error updating tick value: {e}")
            raise

    def get_tick_history(self, ticker: str, limit: int = 10) -> list[tuple]:
        """Get historical tick changes for a specific company.

        Args:
        ----
            ticker (str): Company ticker symbol
            limit (int): Maximum number of history entries to return

        Returns:
        -------
            List[Tuple]: List of (old_tick, new_tick, date, note) tuples

        Raises:
        ------
            Exception: If database query fails

        """
        try:
            return self.conn.execute(
                """
                SELECT old_tick, new_tick, date, note
                FROM tick_history
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """,
                [ticker, limit],
            ).fetchall()
        except Exception as e:
            logger.exception(f"Error getting tick history: {e}")
            raise

    def search_companies(self, search_term: str) -> list[tuple]:
        """Search companies by ticker symbol or name.

        Args:
        ----
            search_term (str): Text to search for in ticker or name

        Returns:
        -------
            List[Tuple]: List of matching (ticker, name, tick) tuples

        Raises:
        ------
            Exception: If database query fails

        """
        try:
            return self.conn.execute(
                """
                SELECT ticker, security_name, tick
                FROM current_universe
                WHERE LOWER(ticker) LIKE ? OR LOWER(security_name) LIKE ?
                ORDER BY tick DESC
                LIMIT 50
            """,
                [f"%{search_term.lower()}%", f"%{search_term.lower()}%"],
            ).fetchall()
        except Exception as e:
            logger.exception(f"Error searching companies: {e}")
            raise

    def cleanup_data(self) -> None:
        """Clean up tick history data by removing invalid entries and duplicates.

        Performs two main cleanup operations:
        1. Removes entries with invalid tick values
        2. Removes duplicate entries while keeping the latest version

        Raises
        ------
            Exception: If database cleanup operation fails

        """
        try:
            # Remove invalid ticks
            self.conn.execute(
                """
                DELETE FROM tick_history
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
            self.conn.execute(
                """
                WITH duplicates AS (
                    SELECT ticker, date
                    FROM tick_history
                    GROUP BY ticker, date
                    HAVING COUNT(*) > 1
                ),
                latest_entries AS (
                    SELECT h.ticker, h.date, h.rowid
                    FROM tick_history h
                    JOIN duplicates d ON h.ticker = d.ticker AND h.date = d.date
                    WHERE h.rowid = (
                        SELECT MAX(rowid)
                        FROM tick_history h2
                        WHERE h2.ticker = h.ticker AND h2.date = h.date
                    )
                )
                DELETE FROM tick_history
                WHERE EXISTS (
                    SELECT 1
                    FROM duplicates d
                    WHERE tick_history.ticker = d.ticker
                    AND tick_history.date = d.date
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM latest_entries le
                    WHERE tick_history.ticker = le.ticker
                    AND tick_history.date = le.date
                    AND tick_history.rowid = le.rowid
                )
            """,
            )
            logger.info("Successfully cleaned up tick history data")
        except Exception as e:
            logger.exception(f"Error cleaning up data: {e}")
            raise


def display_menu() -> None:
    """Display the main menu options for the CLI interface."""


def main() -> None:
    """Main entry point for the CLI application.

    Handles the main program loop and user interaction.

    Raises
    ------
        Exception: If fatal error occurs during execution

    """
    try:
        manager = CLITickManager()

        while True:
            display_menu()
            choice = input("Enter your choice (1-6): ")

            try:
                if choice == "1":
                    companies = manager.get_top_companies()
                    for ticker, _name, _tick in companies:
                        pass

                elif choice == "2":
                    search_term = input("Enter search term: ")
                    results = manager.search_companies(search_term)
                    if results:
                        for ticker, _name, _tick in results:
                            pass
                    else:
                        pass

                elif choice == "3":
                    ticker = input("Enter ticker: ")
                    new_tick = input("Enter new tick value: ")
                    note = input("Enter note: ")
                    manager.update_tick_value(ticker, new_tick, note)

                elif choice == "4":
                    ticker = input("Enter ticker: ")
                    history = manager.get_tick_history(ticker)
                    if history:
                        for _old_tick, new_tick, _date, note in history:
                            pass
                    else:
                        pass

                elif choice == "5":
                    confirm = input("Are you sure you want to cleanup data? (y/n): ")
                    if confirm.lower() == "y":
                        manager.cleanup_data()

                elif choice == "6":
                    break

                else:
                    pass

            except Exception as e:
                logger.exception(f"Error in menu choice {choice}: {e}")

            input("\nPress Enter to continue...")

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
