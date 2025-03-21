#!/usr/bin/env python3
"""
Script to add primary keys to tables in MotherDuck database
that don't have primary keys.
"""

import os
import sys
import yaml
import re
import duckdb
from pathlib import Path
from typing import Dict, List, Any

# Set file paths
CONFIG_PATH = Path("/Users/srvo/dewey/config/dewey.yaml")
ENV_PATH = Path("/Users/srvo/dewey/.env")

def load_env_vars() -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    try:
        with open(ENV_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
        return env_vars
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")
        return {}

def load_config() -> Dict[str, Any]:
    """Load configuration from dewey.yaml."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

def connect_to_motherduck(config: Dict[str, Any]) -> duckdb.DuckDBPyConnection:
    """Connect to MotherDuck database using config settings."""
    # Get connection string from config
    raw_conn_string = config.get('test_database_config', {}).get('motherduck_db', 'md:dewey')
    
    # Process environment variable interpolation
    if "${" in raw_conn_string:
        # Extract environment variable name and default value
        match = re.match(r'\${([^:]+):-([^}]+)}', raw_conn_string)
        if match:
            env_var, default = match.groups()
            db_conn_string = os.environ.get(env_var, default)
        else:
            # Simple environment variable without default
            env_var = raw_conn_string.strip("${}")
            db_conn_string = os.environ.get(env_var, raw_conn_string)
    else:
        db_conn_string = raw_conn_string
    
    print(f"Using connection string: {db_conn_string}")
    
    # First try to get token from .env file
    env_vars = load_env_vars()
    token = env_vars.get('MOTHERDUCK_TOKEN')
    
    # If not in .env, try config file
    if not token:
        token = config.get('test_database_config', {}).get('motherduck_token') or config.get('motherduck_token')
    
    # Last resort: environment variable
    if not token:
        token = os.environ.get('MOTHERDUCK_TOKEN')
        
    if not token:
        print("MotherDuck token not found in .env file, config, or environment variables")
        sys.exit(1)
    
    print(f"Using MotherDuck token: {token[:5]}... (from {'environment' if 'MOTHERDUCK_TOKEN' in os.environ else '.env file' if token == env_vars.get('MOTHERDUCK_TOKEN') else 'config file'})")
    
    # Set the token as environment variable for DuckDB
    os.environ['MOTHERDUCK_TOKEN'] = token
    
    try:
        # Connect to MotherDuck with the proper connection string (read/write mode)
        conn = duckdb.connect(db_conn_string)
        print(f"Connected to MotherDuck database: {db_conn_string}")
        return conn
    except Exception as e:
        print(f"Error connecting to MotherDuck: {e}")
        sys.exit(1)

def add_primary_keys(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Add primary keys to tables in MotherDuck database that don't have one.
    
    The approach:
    1. Check each table for primary keys
    2. For tables without primary keys, add an 'id' column if it doesn't exist
    3. Make it a primary key
    """
    # Get all tables
    tables = conn.execute("SHOW TABLES").fetchall()
    
    for table_row in tables:
        table_name = table_row[0]
        print(f"Checking table: {table_name}")
        
        # Get primary key info
        primary_keys = conn.execute(f"PRAGMA table_info('{table_name}')").fetchdf()
        primary_keys = primary_keys[primary_keys['pk'] > 0]['name'].tolist()
        
        if not primary_keys:
            print(f"Table '{table_name}' doesn't have a primary key.")
            
            # Check if 'id' column exists
            columns = conn.execute(f"PRAGMA table_info('{table_name}')").fetchdf()
            column_names = columns['name'].tolist()
            
            if 'id' in column_names:
                print(f"  'id' column exists - making it a primary key...")
                try:
                    # Add primary key to existing id column
                    conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET PRIMARY KEY")
                    print(f"  Successfully added primary key to 'id' in table '{table_name}'")
                except Exception as e:
                    print(f"  Error setting primary key on existing column: {e}")
            else:
                print(f"  Adding 'id' column as primary key...")
                try:
                    # Create a new id column as primary key
                    # First add the column
                    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN id INTEGER")
                    
                    # Generate sequential IDs
                    conn.execute(f"UPDATE {table_name} SET id = row_number() OVER ()")
                    
                    # Make it a primary key
                    conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET NOT NULL")
                    conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET PRIMARY KEY")
                    print(f"  Successfully added 'id' as primary key to table '{table_name}'")
                except Exception as e:
                    print(f"  Error adding primary key: {e}")
        else:
            print(f"Table '{table_name}' already has primary key(s): {', '.join(primary_keys)}")

def main():
    """Main function."""
    config = load_config()
    conn = connect_to_motherduck(config)
    
    print("Starting to add primary keys to tables...")
    add_primary_keys(conn)
    
    conn.close()
    print("Done!")

if __name__ == "__main__":
    main() 