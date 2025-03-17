import os
import duckdb
from textual.app import App
from textual.binding import Binding
from textual.widgets import DataTable
import logging
import traceback

logger = logging.getLogger(__name__)

class TickManagerApp(App):
    """A TUI application for managing tick ratings."""
    
    # Get the directory of the current file
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    CSS_PATH = os.path.join(CURRENT_DIR, "tick_manager.css")
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("s", "save", "Save", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("p", "toggle_priority", "Toggle Priority Mode", show=True),
        Binding("n", "next_company", "Next Company", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        try:
            logger.info("Initializing TickManagerApp")
            
            # Connect to local DuckDB with concurrent access
            logger.info("Connecting to local DuckDB")
            db_path = os.path.join(self.CURRENT_DIR, 'data.db')
            self.local_conn = duckdb.connect(db_path, access_mode='READ_WRITE', config={'allow_concurrent_access': True})
            logger.info(f"Connected to local database at {db_path}")
            
            # Connect to MotherDuck
            motherduck_token = os.getenv('MOTHERDUCK_TOKEN')
            if not motherduck_token:
                logger.error("MOTHERDUCK_TOKEN environment variable not set")
                raise ValueError("MOTHERDUCK_TOKEN environment variable not set")
            
            # Initialize MotherDuck connection with concurrent access
            logger.info("Connecting to MotherDuck")
            try:
                self.md_conn = duckdb.connect(f'md:?motherduck_token={motherduck_token}', config={'allow_concurrent_access': True})
                self.md_conn.execute("USE port5")
                logger.info("Successfully connected to MotherDuck and selected port5 database")
            except Exception as e:
                logger.error(f"Failed to connect to MotherDuck: {str(e)}")
                raise RuntimeError(f"Failed to connect to MotherDuck: {str(e)}")
            
            self.priority_mode = False
            self.current_priority_index = 0
            self.setup_database()
            logger.info("TickManagerApp initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize TickManagerApp: {str(e)}")
            raise

    def load_companies(self) -> None:
        try:
            logger.info("Starting to load companies")
            table = self.query_one_safe(DataTable, "companies table")
            table.clear()
            
            logger.info("Executing query to fetch companies")
            try:
                logger.info("Verifying database connection")
                self.md_conn.execute("SELECT 1")
                
                query = r"""
                    WITH latest_ticks AS (
                        SELECT 
                            ticker,
                            CASE 
                                WHEN new_tick ~ '^[0-9]+$' THEN TRY_CAST(new_tick AS INTEGER)
                                ELSE 0
                            END as last_tick,
                            monthyear as last_notes,
                            date as last_update
                        FROM (
                            SELECT ticker, new_tick, monthyear, date,
                            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
                            FROM main.tick_history
                        ) ranked
                        WHERE rn = 1
                    )
                    SELECT DISTINCT 
                        TRY_CAST(u.ticker AS VARCHAR) as ticker,
                        TRY_CAST(u.security_name AS VARCHAR) as company_name,
                        COALESCE(t.last_tick, 0)::INTEGER as current_tick,
                        COALESCE(TRY_CAST(t.last_update AS VARCHAR), 'Never')::VARCHAR as last_update,
                        COALESCE(NULLIF(t.last_notes, ''), 'No notes')::VARCHAR as last_notes,
                        CASE 
                            WHEN t.last_update IS NULL THEN 999
                            ELSE DATEDIFF('day', TRY_CAST(t.last_update AS DATE), CURRENT_DATE)
                        END::INTEGER as days_since_review
                    FROM main.current_universe u
                    LEFT JOIN latest_ticks t ON u.ticker = t.ticker
                """
                
                if self.priority_mode:
                    logger.info("Priority mode is enabled, adding priority filters")
                    query += """
                    WHERE (
                        (COALESCE(t.last_tick, 0) > 10 AND (
                            t.last_update IS NULL OR 
                            DATEDIFF('day', TRY_CAST(t.last_update AS DATE), CURRENT_DATE) >= 30
                        ))
                        OR
                        (t.last_update IS NULL OR 
                         DATEDIFF('day', TRY_CAST(t.last_update AS DATE), CURRENT_DATE) >= 90)
                    )
                    """
                
                query += " ORDER BY days_since_review DESC, u.ticker LIMIT 1000"
                
                logger.info("Executing final query")
                logger.debug(f"Query: {query}")
                
                companies = self.md_conn.execute(query).fetchall()
                logger.info(f"Found {len(companies)} companies")
                
                if not companies:
                    logger.warning("No companies found in query result")
                    self.notify("No companies found", severity="warning")
                    return
                
                logger.info("Adding companies to table")
                for idx, company in enumerate(companies):
                    try:
                        logger.debug(f"Processing company {idx + 1}/{len(companies)}: {company}")
                        if not all(isinstance(x, (str, int, float, type(None))) for x in company):
                            logger.warning(f"Invalid data types in company row: {company}")
                            continue
                        table.add_row(*company)
                    except Exception as e:
                        logger.error(f"Error adding row for company {company}: {str(e)}", exc_info=True)
                        continue
                
                logger.info("Companies loaded successfully")
                
            except Exception as e:
                logger.error(f"Database error while loading companies: {str(e)}", exc_info=True)
                self.notify("Database error while loading companies", severity="error")
                raise
                
        except Exception as e:
            logger.error(f"Error loading companies: {str(e)}", exc_info=True)
            self.notify("Error loading companies", severity="error")
            try:
                table = self.query_one(DataTable)
                if table:
                    table.clear()
            except Exception as clear_error:
                logger.error(f"Error clearing table: {str(clear_error)}", exc_info=True)

    def setup_database(self):
        """Setup database tables and validate data integrity."""
        try:
            logger.info("Setting up database tables and validating data integrity")
            
            # Create tick_history table in local DuckDB
            self.local_conn.execute("""
                CREATE TABLE IF NOT EXISTS tick_history (
                    ticker VARCHAR,
                    old_tick VARCHAR,
                    new_tick VARCHAR,
                    date DATE,
                    monthyear VARCHAR
                )
            """)
            
            # Ensure we can read from universe table in MotherDuck
            try:
                self.md_conn.execute("SELECT * FROM main.current_universe LIMIT 1")
                logger.info("Successfully verified access to main.current_universe table")
            except Exception as e:
                logger.error(f"Error accessing MotherDuck universe table: {str(e)}")
                self.notify("Error connecting to MotherDuck universe table", severity="error")
                raise RuntimeError(f"Failed to access MotherDuck universe table: {str(e)}")
            
            # Create or verify tick_history table in MotherDuck
            self.md_conn.execute("""
                CREATE TABLE IF NOT EXISTS main.tick_history (
                    ticker VARCHAR,
                    old_tick VARCHAR,
                    new_tick VARCHAR,
                    date DATE,
                    monthyear VARCHAR
                )
            """)
            
            logger.info("Database setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup database: {str(e)}\n{traceback.format_exc()}")
            raise