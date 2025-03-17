import csv
import os
from sqlalchemy import create_engine, text, Boolean
from sqlalchemy.orm import sessionmaker
from ethifinx.db.models import Exclusion

# Get the absolute paths
base_dir = '/Users/srvo/ethifinx'
csv_path = os.path.join(base_dir, 'data/Port 4.5 - Exclude.csv')
db_path = os.path.join(base_dir, 'data/research.duckdb')

# Connect to existing database
engine = create_engine(f'duckdb:///{db_path}')
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Drop the table if it exists
    session.execute(text('DROP TABLE IF EXISTS exclusions'))
    
    # Create the table with DuckDB-compatible syntax
    create_table_sql = """
    CREATE TABLE exclusions (
        id BIGINT PRIMARY KEY,
        company VARCHAR,
        ticker VARCHAR NOT NULL,
        isin VARCHAR,
        category VARCHAR NOT NULL,
        criteria VARCHAR NOT NULL,
        concerned_groups VARCHAR,
        decision VARCHAR,
        excluded_date VARCHAR,
        notes TEXT,
        is_historical BOOLEAN DEFAULT FALSE,
        excluded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_exclusions_ticker ON exclusions(ticker);
    """
    session.execute(text(create_table_sql))
    session.commit()
    print("Successfully created exclusions table")
    
    # Create a sequence for id
    session.execute(text('CREATE SEQUENCE IF NOT EXISTS exclusions_id_seq'))
    session.commit()
    
    # Insert all records, including duplicates
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not row['Symbol']:
                continue
            
            # Get next id from sequence
            result = session.execute(text('SELECT nextval(\'exclusions_id_seq\')'))
            next_id = result.scalar()
            
            exclusion = Exclusion(
                id=next_id,
                company=row['Company'].strip() if row['Company'] else None,
                ticker=row['Symbol'].strip(),
                isin=row['ISIN'].strip() if row['ISIN'] else None,
                category=row['Category'].strip(),
                criteria=row['Criteria'].strip(),
                concerned_groups=row['Concerned groups'].strip() if row['Concerned groups'] else None,
                decision=row['Decision'].strip() if row['Decision'] else None,
                excluded_date=row['Date'].strip() if row['Date'] else None,
                notes=row['Notes'].strip() if row.get('Notes') else None,
                is_historical=False  # These are current decisions
            )
            session.add(exclusion)
            
        session.commit()
        print("\nSuccessfully populated exclusions table")
        
        # Print some statistics
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT ticker) as unique_companies,
                MAX(excluded_at) as latest_record
            FROM exclusions
        """))
        stats = result.fetchone()
        print(f"\nStatistics:")
        print(f"Total exclusion records: {stats[0]}")
        print(f"Unique companies: {stats[1]}")
        print(f"Latest record: {stats[2]}")
        
except Exception as e:
    session.rollback()
    print(f"Error occurred: {str(e)}")
    raise
finally:
    session.close() 