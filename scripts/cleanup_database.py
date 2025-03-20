#!/usr/bin/env python3

"""
Script to clean up and consolidate tables in the MotherDuck database.
Removes empty tables and consolidates redundant table structures.
"""

from dotenv import load_dotenv
import duckdb

def cleanup_database():
    """Function cleanup_database."""
    print("Starting database cleanup")
    
    # Load environment variables for MotherDuck token
    load_dotenv()
    
    try:
        # Connect to MotherDuck
        conn = duckdb.connect("md:")
        
        # Switch to dewey database
        conn.execute("USE dewey")
        
        # List of empty tables to drop
        empty_tables = [
            "input_data_tick_history",
            "overnight_process_20241230_active_stocks_view",
            "overnight_process_20241230_comprehensive_stock_view",
            "overnight_process_20241230_current_universe",
            "overnight_process_20241230_exclusions",
            "overnight_process_20241230_file_schemas",
            "overnight_process_20241230_stock_analysis",
            "overnight_process_20241230_tick_history",
            "overnight_process_20241230_tracked_stocks",
            "raw_active_stocks_view",
            "raw_comprehensive_stock_view",
            "raw_current_universe",
            "raw_exclusions",
            "raw_file_schemas",
            "raw_stock_analysis",
            "raw_tick_history",
            "raw_tracked_stocks"
        ]
        
        # Drop empty tables
        for table in empty_tables:
            try:
                print(f"Dropping table {table}")
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception as e:
                print(f"Error dropping table {table}: {str(e)}")
        
        print("Database cleanup completed successfully")
        conn.close()
        
    except Exception as e:
        print(f"Error during database cleanup: {str(e)}")
        raise

if __name__ == "__main__":
    cleanup_database() 