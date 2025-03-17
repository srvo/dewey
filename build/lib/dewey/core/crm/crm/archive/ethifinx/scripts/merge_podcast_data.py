import duckdb
import os
from pathlib import Path

def merge_podcast_data():
    """Merge podcast data into the research database."""
    workspace_root = Path(__file__).parent.parent
    podcast_db_path = workspace_root / "data" / "podcast_data.duckdb"
    research_db_path = workspace_root / "data" / "research.duckdb"
    
    # Connect to research database
    research_conn = duckdb.connect(str(research_db_path))
    
    try:
        # Start transaction
        research_conn.execute("BEGIN TRANSACTION")
        
        # Attach podcast database
        research_conn.execute(f"ATTACH '{str(podcast_db_path)}' AS podcast_db")
        
        # Get list of tables from podcast database that actually exist
        tables = research_conn.execute("""
            SELECT DISTINCT table_name 
            FROM podcast_db.information_schema.tables t
            WHERE table_schema = 'main'
            AND EXISTS (
                SELECT 1 
                FROM podcast_db.information_schema.columns c 
                WHERE c.table_name = t.table_name
                AND c.table_schema = 'main'
            )
        """).fetchall()
        
        # Copy each table to research database
        for (table_name,) in tables:
            try:
                print(f"Copying table: {table_name}")
                
                # Test if table exists and has data
                test = research_conn.execute(f"""
                    SELECT COUNT(*) 
                    FROM podcast_db.main.{table_name} 
                    LIMIT 1
                """).fetchone()
                
                if test is None:
                    print(f"Skipping {table_name} - table appears to be empty or non-existent")
                    continue
                
                # Drop existing table if it exists
                research_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Create new table as copy
                research_conn.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM podcast_db.main.{table_name}
                """)
                
                # Get row count
                count = research_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"Copied {count} rows to {table_name}")
                
            except Exception as e:
                print(f"Error processing table {table_name}: {str(e)}")
                continue
        
        # Commit transaction
        research_conn.execute("COMMIT")
        print("Data merge completed successfully")
        
    except Exception as e:
        research_conn.execute("ROLLBACK")
        print(f"Error during merge: {str(e)}")
        raise
        
    finally:
        research_conn.close()

if __name__ == "__main__":
    merge_podcast_data() 