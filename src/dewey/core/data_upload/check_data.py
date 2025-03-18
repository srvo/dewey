#!/usr/bin/env python
import os
import sys
import argparse
from pathlib import Path
from dewey.utils import get_logger
from dewey.core.engines import MotherDuckEngine

def check_table_data(engine, table_name):
    """Check data in a specific table."""
    # Get row count
    count = engine.execute_query(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    
    # Get schema
    schema = engine.execute_query(f"DESCRIBE {table_name}").fetchall()
    
    # Get sample data
    sample = engine.execute_query(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
    
    return {
        'row_count': count,
        'schema': schema,
        'sample': sample
    }

def main():
    parser = argparse.ArgumentParser(description='Check data in MotherDuck database')
    parser.add_argument('--target_db', help='Target database name', default='dewey')
    parser.add_argument('--table', help='Specific table to check', default=None)
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('check_data', log_dir)

    try:
        engine = MotherDuckEngine(args.target_db)
        
        # Get list of tables
        tables = engine.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        tables = [t[0] for t in tables]
        
        if args.table:
            if args.table not in tables:
                logger.error(f"Table {args.table} not found in database {args.target_db}")
                sys.exit(1)
            tables = [args.table]
        
        logger.info(f"Found {len(tables)} tables in database {args.target_db}")
        
        # Check each table
        for table in tables:
            logger.info(f"\nChecking table: {table}")
            
            try:
                data = check_table_data(engine, table)
                
                logger.info(f"Row count: {data['row_count']}")
                logger.info("\nSchema:")
                for col in data['schema']:
                    logger.info(f"  {col[0]}: {col[1]}")
                
                if data['sample']:
                    logger.info("\nSample data:")
                    for row in data['sample']:
                        logger.info(f"  {row}")
                else:
                    logger.warning("No data in table")
                    
            except Exception as e:
                logger.error(f"Error checking table {table}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.close()

if __name__ == '__main__':
    main() 