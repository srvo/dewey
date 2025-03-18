#!/usr/bin/env python3
"""
Cleanup script for MotherDuck tables categorized as "other"
This script helps identify and optionally delete tables that were categorized as "other"
during the schema consolidation process.
"""

import os
import duckdb
import logging
from typing import List, Tuple, Dict
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TableCleaner:
    def __init__(self, database_name: str = "dewey", token: str = None):
        """Initialize the TableCleaner.
        
        Args:
            database_name: Name of the MotherDuck database
            token: MotherDuck token (if None, will try to get from env)
        """
        self.database_name = database_name
        self.token = token or os.environ.get("MOTHERDUCK_TOKEN")
        self._conn = None
        self.connect()
    
    def connect(self) -> None:
        """Initialize connection to MotherDuck database."""
        if not self.token:
            raise ValueError("MotherDuck token is required. Set MOTHERDUCK_TOKEN environment variable.")
        
        try:
            conn_str = f"md:{self.database_name}?motherduck_token={self.token}"
            self._conn = duckdb.connect(conn_str)
            logger.info(f"Connected to MotherDuck database: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MotherDuck: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def get_other_tables(self) -> List[str]:
        """Get list of tables prefixed with 'other_'."""
        try:
            result = self._conn.execute("SHOW TABLES").fetchall()
            return [row[0] for row in result if row[0].startswith('other_')]
        except Exception as e:
            logger.error(f"Failed to list tables: {str(e)}")
            raise
    
    def analyze_table(self, table_name: str) -> Dict:
        """Analyze a table to determine if it's safe to delete.
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Get row count
            row_count = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            # Get schema
            schema = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = [row[0] for row in schema]
            
            # Check if data exists in consolidated tables
            consolidated_tables = self._conn.execute("""
                SHOW TABLES
            """).fetchall()
            consolidated_tables = [t[0] for t in consolidated_tables 
                                if not t[0].startswith('other_') and 
                                not t[0].startswith('temp_')]
            
            data_exists_elsewhere = False
            similar_tables = []
            
            for cons_table in consolidated_tables:
                try:
                    # Check if schemas are compatible
                    cons_schema = self._conn.execute(f"DESCRIBE {cons_table}").fetchall()
                    cons_columns = [row[0] for row in cons_schema]
                    
                    # Check column overlap
                    common_cols = set(columns) & set(cons_columns)
                    if common_cols:
                        # Check for matching data using string comparison to avoid type issues
                        sample_cols = list(common_cols)[:3]  # Use up to 3 common columns for comparison
                        if sample_cols:
                            # Cast all columns to VARCHAR to avoid type conversion issues
                            select_cols = [f"CAST({col} AS VARCHAR) AS {col}" for col in sample_cols]
                            sample_data = self._conn.execute(f"""
                                SELECT {', '.join(select_cols)}
                                FROM {table_name}
                                WHERE {' AND '.join(f"{col} IS NOT NULL" for col in sample_cols)}
                                LIMIT 5
                            """).fetchall()
                            
                            if sample_data:  # Only check if we got valid sample data
                                for row in sample_data:
                                    where_clause = " AND ".join(
                                        f"CAST({col} AS VARCHAR) = ?" for col in sample_cols
                                    )
                                    params = [str(val) if val is not None else None for val in row]
                                    
                                    try:
                                        match_count = self._conn.execute(f"""
                                            SELECT COUNT(*)
                                            FROM {cons_table}
                                            WHERE {where_clause}
                                        """, params).fetchone()[0]
                                        
                                        if match_count > 0:
                                            data_exists_elsewhere = True
                                            similar_tables.append(cons_table)
                                            break
                                    except Exception as e:
                                        logger.debug(f"Error checking matches in {cons_table}: {str(e)}")
                                        continue
                except Exception as e:
                    logger.debug(f"Error analyzing table comparison between {table_name} and {cons_table}: {str(e)}")
                    continue
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'columns': columns,
                'data_exists_elsewhere': data_exists_elsewhere,
                'similar_tables': list(set(similar_tables))
            }
            
        except Exception as e:
            logger.error(f"Error analyzing table {table_name}: {str(e)}")
            return None
    
    def delete_table(self, table_name: str) -> bool:
        """Delete a table.
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            bool indicating success
        """
        try:
            self._conn.execute(f"DROP TABLE {table_name}")
            logger.info(f"Successfully deleted table: {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete table {table_name}: {str(e)}")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup MotherDuck tables categorized as "other"')
    parser.add_argument('--database', default='dewey', help='MotherDuck database name')
    parser.add_argument('--token', help='MotherDuck token (optional, can use MOTHERDUCK_TOKEN env var)')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be deleted')
    parser.add_argument('--force', action='store_true', help='Delete without confirmation')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    cleaner = TableCleaner(database_name=args.database, token=args.token)
    
    try:
        # Get list of "other" tables
        other_tables = cleaner.get_other_tables()
        if not other_tables:
            logger.info("No tables found with 'other_' prefix")
            return
        
        logger.info(f"Found {len(other_tables)} tables with 'other_' prefix")
        
        # Analyze each table with progress bar
        analysis_results = []
        with tqdm(total=len(other_tables), desc="Analyzing tables") as pbar:
            for table in other_tables:
                result = cleaner.analyze_table(table)
                if result:
                    analysis_results.append(result)
                pbar.update(1)
        
        # Display results
        print("\nAnalysis Results:")
        print("=" * 80)
        for result in analysis_results:
            print(f"\nTable: {result['table_name']}")
            print(f"Rows: {result['row_count']}")
            print(f"Columns: {', '.join(result['columns'])}")
            print(f"Data exists in other tables: {'Yes' if result['data_exists_elsewhere'] else 'No'}")
            if result['similar_tables']:
                print(f"Similar tables: {', '.join(result['similar_tables'])}")
            print("-" * 80)
        
        # If not dry run and tables found, confirm deletion
        if not args.dry_run and analysis_results:
            tables_to_delete = [r['table_name'] for r in analysis_results 
                              if r['data_exists_elsewhere']]
            
            if not tables_to_delete:
                logger.info("No tables found that are safe to delete")
                return
            
            if not args.force:
                print(f"\nThe following {len(tables_to_delete)} tables will be deleted:")
                for table in tables_to_delete:
                    print(f"- {table}")
                
                confirm = input("\nDo you want to proceed with deletion? (yes/no): ")
                if confirm.lower() != 'yes':
                    logger.info("Operation cancelled")
                    return
            
            # Delete tables with progress bar
            success_count = 0
            with tqdm(total=len(tables_to_delete), desc="Deleting tables") as pbar:
                for table in tables_to_delete:
                    if cleaner.delete_table(table):
                        success_count += 1
                    pbar.update(1)
            
            logger.info(f"Successfully deleted {success_count} out of {len(tables_to_delete)} tables")
        
        elif args.dry_run:
            deletable_tables = [r['table_name'] for r in analysis_results 
                              if r['data_exists_elsewhere']]
            print(f"\nDry run - {len(deletable_tables)} tables would be deleted:")
            for table in deletable_tables:
                print(f"- {table}")
    
    finally:
        cleaner.close()

if __name__ == '__main__':
    main() 