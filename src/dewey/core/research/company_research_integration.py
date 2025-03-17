#!/usr/bin/env python3
"""
Company Research Integration Script

This script processes company research JSON files and integrates the data into the MotherDuck database.
It handles company information, context, search queries, and research results.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import duckdb
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/company_research_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def connect_to_motherduck(db_name: str = "dewey") -> duckdb.DuckDBPyConnection:
    """
    Connect to the MotherDuck database.
    
    Args:
        db_name: Name of the database to connect to
        
    Returns:
        DuckDB connection object
    """
    try:
        conn = duckdb.connect(f"md:{db_name}")
        logger.info(f"Successfully connected to MotherDuck database '{db_name}'")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MotherDuck database: {e}")
        raise

def ensure_tables_exist(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure all required tables exist in the database."""
    try:
        # Company Research table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_research (
                id VARCHAR PRIMARY KEY,
                company_name VARCHAR,
                ticker VARCHAR,
                description VARCHAR,
                file_path VARCHAR,
                processed_at TIMESTAMP
            )
        """)
        
        # Drop and recreate Company Context table
        try:
            conn.execute("DROP TABLE IF EXISTS company_context")
            logger.info("Dropped company_context table")
        except Exception as e:
            logger.error(f"Error dropping company_context table: {e}")
        
        # Create Company Context table
        conn.execute("""
            CREATE TABLE company_context (
                id VARCHAR PRIMARY KEY,
                company_research_id VARCHAR,
                context_type VARCHAR,
                content VARCHAR,
                context_text VARCHAR,
                FOREIGN KEY (company_research_id) REFERENCES company_research(id)
            )
        """)
        logger.info("Created company_context table")
        
        # Company Search Queries table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_search_queries (
                id VARCHAR PRIMARY KEY,
                company_research_id VARCHAR,
                category VARCHAR,
                query VARCHAR,
                FOREIGN KEY (company_research_id) REFERENCES company_research(id)
            )
        """)
        
        # Company Research Results table - updated to match actual structure
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_research_results (
                id VARCHAR PRIMARY KEY,
                company_research_id VARCHAR,
                title VARCHAR,
                content VARCHAR,
                source VARCHAR,
                date VARCHAR,
                category VARCHAR,
                FOREIGN KEY (company_research_id) REFERENCES company_research(id)
            )
        """)
        
        logger.info("All required tables exist")
    except Exception as e:
        logger.error(f"Error ensuring tables exist: {e}")
        raise

def process_file(conn: duckdb.DuckDBPyConnection, file_path: str) -> None:
    """Process a single JSON file and update the database."""
    try:
        logger.info(f"Processing file: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract research ID from filename
        file_name = os.path.basename(file_path)
        research_id = os.path.splitext(file_name)[0]
        
        # Extract company information
        company_name = data.get('company_name', '')
        ticker = data.get('ticker', '')
        description = data.get('description', '')
        
        # Insert into company_research table
        conn.execute("""
            INSERT INTO company_research (id, company_name, ticker, description, file_path, processed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                ticker = EXCLUDED.ticker,
                description = EXCLUDED.description,
                file_path = EXCLUDED.file_path,
                processed_at = EXCLUDED.processed_at
        """, [research_id, company_name, ticker, description, file_path, pd.Timestamp.now()])
        
        # Process company context
        company_context = data.get('company_context')
        process_company_context(conn, research_id, company_context)
        
        # Process search queries
        search_queries = data.get('search_queries', [])
        process_search_queries(conn, research_id, search_queries)
        
        # Process research results
        research_results = data.get('research_results', {})
        process_research_results(conn, research_id, research_results)
        
        logger.info(f"Successfully processed file: {file_path}")
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        raise

def process_company_context(conn: duckdb.DuckDBPyConnection, research_id: str, context: Union[Dict[str, Any], str, None]) -> None:
    """Process company context information and update the database."""
    try:
        if context is None:
            logger.warning(f"No context provided for research: {research_id}")
            return
        
        # Handle different context types
        if isinstance(context, str):
            # Insert as a general overview
            conn.execute("""
                INSERT INTO company_context (id, company_research_id, context_type, content, context_text)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    context_text = EXCLUDED.context_text
            """, [f"{research_id}_overview", research_id, "overview", context, context])
        elif isinstance(context, dict):
            # Process each context section as a separate entry
            for context_type, content in context.items():
                if content:  # Only process non-empty content
                    content_str = content if isinstance(content, str) else json.dumps(content)
                    conn.execute("""
                        INSERT INTO company_context (id, company_research_id, context_type, content, context_text)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            context_text = EXCLUDED.context_text
                    """, [f"{research_id}_{context_type}", research_id, context_type, content_str, content_str])
        else:
            logger.warning(f"Unexpected context type for research {research_id}: {type(context)}")
            return
            
        logger.info(f"Successfully processed context for research: {research_id}")
    except Exception as e:
        logger.error(f"Error processing context for research {research_id}: {e}")
        raise

def process_search_queries(conn: duckdb.DuckDBPyConnection, research_id: str, queries: List[Dict[str, Any]]) -> None:
    """
    Process search queries and update the database.
    
    Args:
        conn: DuckDB connection object
        research_id: ID of the parent company research
        queries: List of search query dictionaries
    """
    try:
        # Delete existing queries for this research
        conn.execute("""
        DELETE FROM company_search_queries WHERE company_research_id = ?
        """, (research_id,))
        
        # Process each query
        for i, query_data in enumerate(queries):
            conn.execute("""
            INSERT INTO company_search_queries (id, company_research_id, category, query)
            VALUES (?, ?, ?, ?)
            """, (
                f"{research_id}_query_{i}",
                research_id,
                query_data.get('category', ''),
                query_data.get('query', '')
            ))
        
        logger.info(f"Successfully processed search queries for research: {research_id}")
    except Exception as e:
        logger.error(f"Error processing search queries for research {research_id}: {e}")
        raise

def process_research_results(conn: duckdb.DuckDBPyConnection, research_id: str, results: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
    """Process research results and update the database."""
    try:
        if not results:
            logger.warning(f"No research results provided for research: {research_id}")
            return
        
        # Handle both list and dictionary formats
        if isinstance(results, list):
            # Process each result in the list
            for i, result in enumerate(results):
                if not isinstance(result, dict):
                    logger.warning(f"Skipping invalid result format for research {research_id}, index {i}")
                    continue
                    
                # Extract data from the result dictionary
                title = result.get('recommendation', result.get('title', ''))
                content = result.get('summary', result.get('content', ''))
                source = result.get('source', 'research_analysis')
                date = result.get('date', '')
                category = result.get('category', 'research')
                
                # Insert into company_research_results table
                conn.execute("""
                    INSERT INTO company_research_results (id, company_research_id, title, content, source, date, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        source = EXCLUDED.source,
                        date = EXCLUDED.date,
                        category = EXCLUDED.category
                """, [f"{research_id}_results_{i}", research_id, title, content, source, date, category])
        else:
            # Handle dictionary format (original behavior)
            title = results.get('recommendation', results.get('title', ''))
            content = results.get('summary', results.get('content', ''))
            source = results.get('source', 'research_analysis')
            date = results.get('date', '')
            category = results.get('category', 'research')
            
            # Insert into company_research_results table
            conn.execute("""
                INSERT INTO company_research_results (id, company_research_id, title, content, source, date, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    source = EXCLUDED.source,
                    date = EXCLUDED.date,
                    category = EXCLUDED.category
            """, [f"{research_id}_results", research_id, title, content, source, date, category])
        
        logger.info(f"Successfully processed research results for research: {research_id}")
    except Exception as e:
        logger.error(f"Error processing research results for research {research_id}: {e}")
        raise

def process_directory(directory: str, conn: duckdb.DuckDBPyConnection) -> None:
    """
    Process all JSON files in a directory.
    
    Args:
        directory: Directory path containing JSON files
        conn: DuckDB connection object
    """
    try:
        logger.info(f"Processing directory: {directory}")
        
        # Get all JSON files in the directory
        json_files = [f for f in os.listdir(directory) if f.endswith('.json') and not f.endswith('.metadata')]
        
        # Process each file
        processed_count = 0
        for file_name in json_files:
            if file_name.endswith('_research.json'):
                file_path = os.path.join(directory, file_name)
                try:
                    process_file(conn, file_path)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    # Continue with next file instead of failing the entire process
                    continue
        
        logger.info(f"Successfully processed {processed_count} files in directory: {directory}")
    except Exception as e:
        logger.error(f"Error processing directory {directory}: {e}")
        raise

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Process company research JSON files and update the database.')
    parser.add_argument('--db', type=str, default='dewey', help='MotherDuck database name')
    parser.add_argument('--input-dir', type=str, required=True, help='Directory containing JSON files')
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    try:
        # Connect to MotherDuck
        conn = connect_to_motherduck(args.db)
        
        # Ensure tables exist
        ensure_tables_exist(conn)
        
        # Process the directory
        process_directory(args.input_dir, conn)
        
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 