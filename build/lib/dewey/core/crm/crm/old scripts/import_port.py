from pathlib import Path
import duckdb
from db import get_connection, execute_query

def import_from_port(port_db_path: str):
    """Import companies from Port database"""
    print(f"Importing companies from: {port_db_path}")
    
    try:
        # Connect to Port database
        port_conn = duckdb.connect(port_db_path, read_only=True)
        
        # Get companies from Port
        companies = port_conn.execute("""
            SELECT DISTINCT 
                name,
                industry,
                website,
                description,
                headquarters_city || ', ' || headquarters_country as headquarters,
                founded_year::VARCHAR as founded
            FROM companies
            WHERE name IS NOT NULL
        """).fetchall()
        
        print(f"Found {len(companies)} companies")
        
        # Import to research database
        with get_connection() as conn:
            for i, company in enumerate(companies, 1):
                try:
                    conn.execute("""
                        INSERT INTO companies (name, industry, website, description, headquarters, founded)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT (name) DO UPDATE SET
                            industry = EXCLUDED.industry,
                            website = EXCLUDED.website,
                            description = EXCLUDED.description,
                            headquarters = EXCLUDED.headquarters,
                            founded = EXCLUDED.founded,
                            updated_at = CURRENT_TIMESTAMP
                    """, company)
                    
                    if i % 100 == 0:
                        print(f"Imported {i} companies...")
                        
                except Exception as e:
                    print(f"Error importing {company[0]}: {str(e)}")
                    continue
        
        print("\nImport completed!")
        
        # Verify import
        count = execute_query("SELECT COUNT(*) FROM companies")[0][0]
        print(f"Total companies in database: {count}")
        
    except Exception as e:
        print(f"Import failed: {str(e)}")
    finally:
        port_conn.close()

if __name__ == "__main__":
    # Assuming port.duckdb is in the data directory
    PORT_DB = Path("/Users/srvo/notebooks/data/port.duckdb")
    
    if not PORT_DB.exists():
        print(f"Port database not found at: {PORT_DB}")
        exit(1)
    
    import_from_port(str(PORT_DB)) 