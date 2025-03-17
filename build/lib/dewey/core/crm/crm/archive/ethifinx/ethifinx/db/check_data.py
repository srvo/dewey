"""Script to check data in DuckDB tables."""

from .duckdb_store import get_connection

def main():
    """Check data in DuckDB tables."""
    with get_connection() as conn:
        # Get list of all tables
        tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        print("\nAll tables in DuckDB:")
        print("-" * 40)
        
        for (table_name,) in tables:
            # Get record count
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"\n{table_name}:")
            print(f"Total records: {count}")
            
            if count > 0:
                # Show sample data
                print("Sample records:")
                results = conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
                for row in results:
                    print(row)

if __name__ == "__main__":
    main() 