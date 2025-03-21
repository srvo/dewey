#!/usr/bin/env python3
"""
Script to check imported emails in the MotherDuck database.
"""

import os
import duckdb
import json
from pathlib import Path

# Load environment variables
env_path = Path("/Users/srvo/dewey/.env")
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

# Connect to MotherDuck
token = os.environ.get('MOTHERDUCK_TOKEN')
if not token:
    print("MotherDuck token not found. Check .env file.")
    exit(1)

# Set token in environment variable
os.environ['MOTHERDUCK_TOKEN'] = token

# Connect to database
connection_string = "md:dewey"
try:
    conn = duckdb.connect(connection_string)
    print(f"Connected to MotherDuck database: {connection_string}")
    
    # Check count of emails
    count_result = conn.execute("SELECT COUNT(*) FROM emails").fetchone()
    print(f"Number of emails in database: {count_result[0]}")
    
    # Check table schema
    print("\nTable schema:")
    schema_result = conn.execute("PRAGMA table_info('emails')").fetchdf()
    print(schema_result)
    
    # Check sample emails with available columns
    if count_result[0] > 0:
        print("\nSample emails:")
        result = conn.execute("""
            SELECT msg_id, subject, from_address 
            FROM emails 
            LIMIT 3
        """).fetchdf()
        print(result)
    
    # Close connection
    conn.close()
    
except Exception as e:
    print(f"Error connecting to MotherDuck: {e}") 