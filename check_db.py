#!/usr/bin/env python3
"""
Utility script to check the structure of a DuckDB database.
"""

import os
import sys
import duckdb

def main():
    """Main function to check DuckDB structure."""
    db_path = "/Users/srvo/dewey/dewey.duckdb"
    print(f"Checking database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file does not exist at {db_path}")
        return 1
    
    print(f"File size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")
    
    try:
        # Connect to the database
        conn = duckdb.connect(db_path)
        print("Connected to database successfully")
        
        # Check if database has any tables
        tables = conn.execute("SHOW TABLES").fetchall()
        if not tables:
            print("No tables found in the database")
            return 1
        
        print(f"Found {len(tables)} tables:")
        for i, table in enumerate(tables):
            table_name = table[0]
            print(f"{i+1}. {table_name}")
            
            # Get row count for this table
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"   - {count} rows")
                
                # If table has rows, show a sample
                if count > 0:
                    sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
                    print(f"   - Sample data: {sample}")
                    
                    # Get column info
                    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                    print(f"   - Columns ({len(columns)}):")
                    for col in columns:
                        col_name = col[1]
                        col_type = col[2]
                        print(f"      - {col_name} ({col_type})")
            except Exception as e:
                print(f"   - Error inspecting table: {e}")
        
        # Close the connection
        conn.close()
        print("Database check completed successfully")
        
    except Exception as e:
        print(f"Error examining database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 