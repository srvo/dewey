import duckdb
import os

def check_tables(conn, env_name):
    print(f"\n=== Checking {env_name} Database ===")
    
    try:
        # Get list of all tables
        result = conn.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('main_raw', 'main_staging', 'main_intermediate', 'main_mart', 'snapshots')
            ORDER BY table_schema, table_name
        """).fetchall()
        
        current_schema = None
        for schema, table in result:
            if schema != current_schema:
                print(f"\n{schema}:")
                current_schema = schema
            
            try:
                count = conn.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"').fetchone()[0]
                print(f"  ✓ {table}: {count} records")
            except Exception as e:
                print(f"  ✗ {table}: Error - {str(e)}")
                
    except Exception as e:
        print(f"Error listing tables: {str(e)}")

try:
    # Check MotherDuck
    print("\nConnecting to MotherDuck...")
    token = os.environ.get('MOTHERDUCK_TOKEN')
    if not token:
        print("Error: MOTHERDUCK_TOKEN environment variable not set")
    else:
        with duckdb.connect(f"md:port5?motherduck_token={token}") as md_conn:
            check_tables(md_conn, "MotherDuck")

    # Check Local
    print("\nConnecting to Local DuckDB...")
    with duckdb.connect("data/local.duckdb") as local_conn:
        check_tables(local_conn, "Local")

except Exception as e:
    print(f"Error: {str(e)}") 