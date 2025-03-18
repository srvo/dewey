#!/usr/bin/env python3
"""
Quick script to drop all tables that begin with 'other_'
"""

import duckdb
import os
from tqdm import tqdm

# Connect to MotherDuck
token = os.environ.get("MOTHERDUCK_TOKEN")
if not token:
    raise ValueError("MOTHERDUCK_TOKEN environment variable not set")

conn = duckdb.connect(f"md:dewey?motherduck_token={token}")

try:
    # Get list of tables starting with 'other_'
    tables = conn.execute("SHOW TABLES").fetchall()
    other_tables = [t[0] for t in tables if t[0].startswith('other_')]
    
    print(f"Found {len(other_tables)} tables to drop")
    
    # Drop tables with progress bar
    with tqdm(total=len(other_tables), desc="Dropping tables") as pbar:
        for table in other_tables:
            try:
                conn.execute(f"DROP TABLE {table}")
                pbar.set_description(f"Dropped {table}")
            except Exception as e:
                print(f"\nError dropping {table}: {str(e)}")
            pbar.update(1)
    
    print("\nDone!")
    print(f"Successfully dropped {len(other_tables)} tables")

finally:
    conn.close() 