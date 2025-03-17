#!/usr/bin/env python3
"""Simple test script to check database connection and module imports."""

import os
import sys
from pathlib import Path
import duckdb

# Add the project root to the Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

print("Simple test script running")
print(f"Project root: {project_root}")
print(f"DuckDB version: {duckdb.__version__}")

# Test database connection
try:
    print("\nTesting direct DuckDB connection with a test database...")
    # Use a test database path
    test_db_path = os.path.expanduser("~/dewey_test.duckdb")
    print(f"Connecting to test database at: {test_db_path}")
    
    # Try direct connection to a new test database
    conn = duckdb.connect(test_db_path)
    print("Direct DuckDB connection successful!")
    
    # Drop the test table if it exists to avoid duplicate key errors
    conn.execute("DROP TABLE IF EXISTS test_table")
    
    # Create a test table
    conn.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            value INTEGER
        )
    """)
    print("Created test table")
    
    # Insert some test data
    conn.execute("""
        INSERT INTO test_table (id, name, value) VALUES
        (1, 'test1', 100),
        (2, 'test2', 200),
        (3, 'test3', 300)
    """)
    print("Inserted test data")
    
    # Query the test data
    result = conn.execute("SELECT * FROM test_table").fetchall()
    print("Test data:")
    for row in result:
        print(f"  {row}")
    
    # List all tables
    print("Available tables:")
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for table in tables:
        print(f"- {table[0]}")
        
    conn.close()
    print("Database test completed successfully!")
    
except Exception as e:
    print(f"Database test error: {e}")
    import traceback
    traceback.print_exc()

# Test module imports
try:
    print("\nTesting module imports...")
    
    # Test structlog import
    print("Importing structlog...")
    import structlog
    print(f"structlog version: {structlog.__version__}")
    
    # Test requests import
    print("Importing requests...")
    import requests
    print(f"requests version: {requests.__version__}")
    
    # Test tenacity import
    print("Importing tenacity...")
    import tenacity
    # tenacity doesn't have a __version__ attribute, so we'll just check if it's imported
    print(f"tenacity imported successfully: {tenacity.__name__}")
    
    print("All module imports successful!")
    
except Exception as e:
    print(f"Module import error: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed successfully!")

if __name__ == "__main__":
    print("Script executed directly") 