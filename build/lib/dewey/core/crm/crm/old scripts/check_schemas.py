from pathlib import Path
from ..utils.schema import find_duckdb_files, get_table_schema, get_table_sample
from ..db import get_connection, DATA_DIR
import duckdb

def check_schemas():
    """Check and compare database schemas"""
    # Find DuckDB files
    duckdb_files = find_duckdb_files(DATA_DIR)
    if not duckdb_files:
        print("No DuckDB files found in data directory")
        return
        
    print("Found DuckDB files:")
    for db_file in duckdb_files:
        print(f"\nAnalyzing: {db_file}")
        conn = duckdb.connect(str(db_file), read_only=True)
        
        try:
            # Get tables
            tables = conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main'
                ORDER BY table_name
            """).fetchall()
            
            if not tables:
                print("  No tables found")
                continue
                
            # Analyze each table
            for (table,) in tables:
                print(f"\n- Table: {table}")
                
                # Get schema
                schema = get_table_schema(conn, table)
                print("  Schema:")
                for col, dtype, nullable in schema:
                    print(f"    {col}: {dtype} {'(nullable)' if nullable == 'YES' else ''}")
                
                # Get sample
                count, columns, sample = get_table_sample(conn, table)
                print(f"\n  Row count: {count}")
                
                if sample:
                    print("  Sample row:")
                    for col, val in zip(columns, sample[0]):
                        print(f"    {col}: {val}")
                
                print("-" * 50)
                
        finally:
            conn.close()

if __name__ == "__main__":
    check_schemas() 