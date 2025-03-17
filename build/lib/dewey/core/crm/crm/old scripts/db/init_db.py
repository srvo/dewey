import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from schema import Base

def setup_database():
    admin_url = os.getenv(
        "DB_ADMIN_URL",
        "postgresql://localhost/template1"  # Use template1 as default admin DB
    )
    
    # Derive default DB_URL from admin URL
    admin_parsed = make_url(admin_url)
    db_url = os.getenv("DB_URL", str(admin_parsed.set(database="crm_enrichment")))
    
    # Verify connection to admin database
    try:
        # Create admin engine with autocommit isolation
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            # Check if database exists first
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname='crm_enrichment'")
            )
            
            if not result.scalar():
                conn.execute(text("CREATE DATABASE crm_enrichment"))
                print("Created database 'crm_enrichment'")
            else:
                print("Database 'crm_enrichment' already exists")

    except Exception as e:
        print(f"Database creation error: {str(e)}")
        print("\nTROUBLESHOOTING:")
        print("1. Ensure PostgreSQL is running (brew services start postgresql@16)")
        print("2. Create a .env file with your database credentials:")
        print("   DB_ADMIN_URL=postgresql://localhost/template1?user=<YOUR_USERNAME>")
        print("3. If using password auth, add: &password=<YOUR_PASSWORD>")
        return False

    # Create tables
    try:
        engine = create_engine(db_url)
        
        # Drop all tables first if they exist
        Base.metadata.drop_all(engine)
        print("Dropped existing tables")
        
        # Create fresh tables
        Base.metadata.create_all(engine)
        print("Created tables successfully!")
        
        # Verify schema
        insp = inspect(engine)
        if 'attio_contacts' not in insp.get_table_names():
            raise RuntimeError("attio_contacts table was not created")
            
        cols = insp.get_columns('attio_contacts')
        if not any(c['name'] == 'record_id' for c in cols):
            raise RuntimeError("record_id column missing in attio_contacts")
            
        return True
    except Exception as e:
        print(f"Table creation error: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    if setup_database():
        sys.exit(0)
    sys.exit(1)
