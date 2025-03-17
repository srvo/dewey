from pathlib import Path
import pandas as pd
from ..db import get_connection, insert_company

def setup_database():
    """Create research database tables if they don't exist"""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                ticker VARCHAR,
                isin VARCHAR,
                tick INTEGER,
                industry VARCHAR,
                category VARCHAR,
                sector VARCHAR,
                description TEXT,
                last_tick_date DATE,
                workflow VARCHAR,
                excluded BOOLEAN DEFAULT FALSE,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def import_universe():
    """Import companies from Universe.csv"""
    csv_path = Path("/Users/srvo/notebooks/data/Universe.csv")
    
    if not csv_path.exists():
        print(f"Universe.csv not found at: {csv_path}")
        return
    
    # Ensure database is setup
    setup_database()
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Clean and prepare data
    required_columns = ['Excluded', 'Workflow', 'Ticker', 'ISIN', 'Tick', 
                       'Security Name', 'Note', 'Last Tick Date', 'Category', 'Sector']
    
    if not all(col in df.columns for col in required_columns):
        print("Warning: Some expected columns are missing")
    
    print(f"Found {len(df)} entries")
    
    # Import each company
    with get_connection() as conn:
        for _, row in df.iterrows():
            try:
                # Skip if explicitly excluded
                if pd.notna(row.get('Excluded')) and row['Excluded'].lower() == 'exclude':
                    continue
                
                # Convert tick date if present
                tick_date = None
                if pd.notna(row.get('Last Tick Date')):
                    try:
                        tick_date = pd.to_datetime(row['Last Tick Date']).date()
                    except:
                        pass
                
                query = """
                    INSERT INTO companies (
                        name, ticker, isin, tick, industry, category, 
                        sector, description, last_tick_date, workflow, 
                        excluded, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (name) DO UPDATE SET
                        ticker=excluded.ticker,
                        tick=excluded.tick,
                        last_tick_date=excluded.last_tick_date,
                        note=excluded.note
                    RETURNING id
                """
                
                result = conn.execute(query, (
                    row.get('Security Name'),
                    row.get('Ticker'),
                    row.get('ISIN'),
                    row.get('Tick'),
                    None,  # industry (derived later)
                    row.get('Category'),
                    row.get('Sector'),
                    row.get('Note'),
                    tick_date,
                    row.get('Workflow'),
                    row.get('Excluded') == 'Exclude',
                    row.get('Note')
                )).fetchone()
                
                if result:
                    print(f"Added/Updated: {row['Security Name']} ({row.get('Ticker', 'No Ticker')}) - {row.get('Category', 'No Category')}")
                
            except Exception as e:
                print(f"Error processing {row.get('Security Name', 'Unknown')}: {str(e)}")
    
    print("\nImport complete!")

if __name__ == "__main__":
    import_universe() 