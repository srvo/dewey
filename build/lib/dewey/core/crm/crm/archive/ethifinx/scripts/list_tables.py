import duckdb
from pathlib import Path

def list_tables():
    """List all tables in the port database."""
    workspace_root = Path(__file__).parent.parent
    port_db_path = workspace_root / "data" / "port.duckdb"
    
    # Connect to database
    conn = duckdb.connect(str(port_db_path))
    
    try:
        # Get all tables
        tables = conn.execute("""
            SELECT 
                table_schema,
                table_name,
                (
                    SELECT COUNT(*) 
                    FROM (
                        SELECT * FROM main."${table_name}" LIMIT 1
                    )
                ) as has_data
            FROM information_schema.tables 
            WHERE table_schema IN ('main', 'public')
            ORDER BY table_schema, table_name
        """).fetchall()
        
        print(f"\nTables in {port_db_path}:")
        print("-" * 50)
        for schema, table, has_data in tables:
            status = "with data" if has_data > 0 else "empty"
            print(f"{schema}.{table} ({status})")
            
            # Show sample data if table has content
            if has_data > 0:
                sample = conn.execute(f"""
                    SELECT * FROM "{table}" LIMIT 3
                """).fetchall()
                print("Sample data:")
                for row in sample:
                    print(f"  {row}")
                print()
        
    finally:
        conn.close()

if __name__ == "__main__":
    list_tables() 