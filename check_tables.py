#!/usr/bin/env python3
"""Simple script to check the DuckDB database tables."""

import os
import sys
import duckdb

def main():
    """Main function to check database tables."""
    # Define the database path
    db_path = os.path.join(os.getcwd(), "dewey.duckdb")
    
    print(f"Checking database at: {db_path}")
    
    # Check if the file exists
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return
    
    # Report the file size
    size_bytes = os.path.getsize(db_path)
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_mb / 1024
    print(f"Database file size: {size_bytes:,} bytes ({size_mb:.2f} MB / {size_gb:.2f} GB)")
    
    try:
        # Connect to the database
        conn = duckdb.connect(db_path)
        print("Connected to the database successfully")
        
        # List all tables
        print("\n=== Tables in the database ===")
        tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        tables_result = conn.execute(tables_query).fetchall()
        tables = [row[0] for row in tables_result]
        
        if not tables:
            print("No tables found in the database")
            conn.close()
            return
        
        print(f"Found {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  - {table}")
        
        # Check key tables
        key_tables = ['emails', 'email_analyses', 'master_clients']
        for table in key_tables:
            if table in tables:
                # Show table schema
                print(f"\n=== Schema for '{table}' table ===")
                schema_query = f"PRAGMA table_info({table})"
                schema_result = conn.execute(schema_query).fetchall()
                columns = [(row[1], row[2]) for row in schema_result]
                for name, type_name in columns:
                    print(f"  {name:<20} {type_name}")
                
                # Count rows
                count_query = f"SELECT COUNT(*) FROM {table}"
                count_result = conn.execute(count_query).fetchone()
                row_count = count_result[0] if count_result else 0
                print(f"\nRow count: {row_count:,}")
                
                # Show sample data (first 5 rows)
                if row_count > 0:
                    print(f"\nSample data from '{table}' (first 5 rows):")
                    sample_query = f"SELECT * FROM {table} LIMIT 5"
                    sample_result = conn.execute(sample_query)
                    
                    # Get column names from description
                    if hasattr(sample_result, 'description'):
                        col_names = [col[0] for col in sample_result.description]
                        print("  " + " | ".join(col_names))
                        print("  " + "-" * 80)
                        
                        rows = sample_result.fetchall()
                        for row in rows:
                            # Truncate long values for display
                            display_row = []
                            for val in row:
                                if val is None:
                                    display_row.append("NULL")
                                elif isinstance(val, str) and len(val) > 50:
                                    display_row.append(val[:47] + "...")
                                else:
                                    display_row.append(str(val))
                            print("  " + " | ".join(display_row))
                    else:
                        print("  Unable to get column information")
            else:
                print(f"\nTable '{table}' not found in the database")
        
        # Close the connection
        conn.close()
        print("\nDatabase check completed")
        
    except Exception as e:
        print(f"Error while checking database: {e}")
        import traceback
        traceback.print_exc()
    
if __name__ == "__main__":
    main() 