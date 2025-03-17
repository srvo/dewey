import csv
import os
import sys
from datetime import datetime, UTC

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.stock import Base, TrackedStock

def clean_string(s):
    """Clean a string by removing newlines and extra whitespace"""
    if not s:
        return None
    return s.strip()

def setup_db():
    engine = create_engine('postgresql+psycopg2://postgres:password@localhost:5432/postgres')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def add_port45_stocks():
    session = setup_db()
    
    # Get the absolute path to the CSV file - look in workspace root
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'Port 4.5 - Universe-4.csv')
    print(f"Looking for CSV file at: {csv_path}")
    
    # Read the CSV file
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows where Excluded is "Exclude"
            if row['Excluded'] == 'Exclude':
                continue
                
            # Clean the data
            symbol = clean_string(row['Ticker'])
            isin = clean_string(row['ISIN'])
            name = clean_string(row['Security Name'])
            notes = clean_string(row['Note'])
            
            if not symbol:  # Skip if no ticker symbol
                continue
                
            # Check if stock already exists
            existing = session.query(TrackedStock).filter_by(symbol=symbol).first()
            if not existing:
                try:
                    stock = TrackedStock(
                        symbol=symbol,
                        name=name,
                        isin=isin,
                        notes=notes,
                        added_date=datetime.now(UTC),
                        is_active=True
                    )
                    session.add(stock)
                    print(f"Adding stock: {symbol} - {name}")
                    session.commit()  # Commit after each successful add
                except Exception as e:
                    print(f"Error adding stock {symbol}: {str(e)}")
                    session.rollback()
    
    session.close()

if __name__ == "__main__":
    add_port45_stocks() 