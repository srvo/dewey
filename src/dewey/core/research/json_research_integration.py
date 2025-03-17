#!/usr/bin/env python3
"""
JSON Research Integration Script
===============================

This script integrates company research information from JSON files into the MotherDuck database.
It processes JSON files containing company research data and updates the research tables.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import duckdb
import pandas as pd

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"json_research_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("json_research_integration")

def connect_to_motherduck(database_name: str = "dewey") -> duckdb.DuckDBPyConnection:
    """Connect to the MotherDuck database.
    
    Args:
        database_name: Name of the MotherDuck database
        
    Returns:
        DuckDB connection
    """
    try:
        conn = duckdb.connect(f"md:{database_name}")
        logger.info(f"Connected to MotherDuck database: {database_name}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to MotherDuck database: {e}")
        raise

def ensure_tables_exist(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure that the necessary tables exist in the database.
    
    Args:
        conn: DuckDB connection
    """
    try:
        # Check if company_research table exists
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_research'").fetchone()
        if not result:
            logger.info("Creating company_research table")
            conn.execute("""
            CREATE TABLE company_research (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR,
                company_name VARCHAR,
                description VARCHAR,
                company_context VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        # Check if company_research_queries table exists
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_research_queries'").fetchone()
        if not result:
            logger.info("Creating company_research_queries table")
            conn.execute("""
            CREATE TABLE company_research_queries (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                company_ticker VARCHAR,
                category VARCHAR,
                query VARCHAR,
                rationale VARCHAR,
                priority INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        # Check if company_research_results table exists
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_research_results'").fetchone()
        if not result:
            logger.info("Creating company_research_results table")
            conn.execute("""
            CREATE TABLE company_research_results (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                company_ticker VARCHAR,
                category VARCHAR,
                query VARCHAR,
                rationale VARCHAR,
                priority INTEGER,
                web_results JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        logger.info("Tables verified/created successfully")
    except Exception as e:
        logger.error(f"Error ensuring tables exist: {e}")
        raise

def process_json_file(file_path: str) -> Dict[str, Any]:
    """Process a JSON file containing company research data.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the parsed JSON data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Successfully processed JSON file: {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error processing JSON file {file_path}: {e}")
        return {}

def update_company_research(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> None:
    """Update the company_research table with data from the JSON file.
    
    Args:
        conn: DuckDB connection
        data: Dictionary containing company research data
    """
    try:
        if not data or 'company' not in data:
            logger.warning("No company data found in the JSON file")
            return
        
        company = data['company']
        ticker = company.get('ticker')
        
        if not ticker:
            logger.warning("No ticker found in the company data")
            return
        
        # Check if company already exists
        result = conn.execute(f"SELECT ticker FROM company_research WHERE ticker = '{ticker}'").fetchone()
        
        if result:
            # Update existing company
            logger.info(f"Updating existing company: {ticker}")
            conn.execute("""
            UPDATE company_research SET
                company_name = ?,
                description = ?,
                company_context = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticker = ?
            """, [
                company.get('name'),
                company.get('description'),
                data.get('company_context'),
                ticker
            ])
        else:
            # Insert new company
            logger.info(f"Inserting new company: {ticker}")
            conn.execute("""
            INSERT INTO company_research (
                ticker, company_name, description, company_context
            ) VALUES (?, ?, ?, ?)
            """, [
                ticker,
                company.get('name'),
                company.get('description'),
                data.get('company_context')
            ])
        
        logger.info(f"Successfully updated company_research table for {ticker}")
    except Exception as e:
        logger.error(f"Error updating company_research table: {e}")
        raise

def update_company_research_queries(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> None:
    """Update the company_research_queries table with data from the JSON file.
    
    Args:
        conn: DuckDB connection
        data: Dictionary containing company research data
    """
    try:
        if not data or 'company' not in data or 'search_queries' not in data:
            logger.warning("No company or search queries data found in the JSON file")
            return
        
        company = data['company']
        ticker = company.get('ticker')
        search_queries = data.get('search_queries', [])
        
        if not ticker:
            logger.warning("No ticker found in the company data")
            return
        
        if not search_queries:
            logger.warning(f"No search queries found for {ticker}")
            return
        
        # Delete existing queries for this company
        conn.execute(f"DELETE FROM company_research_queries WHERE company_ticker = '{ticker}'")
        
        # Insert new queries
        for query in search_queries:
            conn.execute("""
            INSERT INTO company_research_queries (
                company_ticker, category, query, rationale, priority
            ) VALUES (?, ?, ?, ?, ?)
            """, [
                ticker,
                query.get('category'),
                query.get('query'),
                query.get('rationale'),
                query.get('priority')
            ])
        
        logger.info(f"Successfully updated company_research_queries table for {ticker} with {len(search_queries)} queries")
    except Exception as e:
        logger.error(f"Error updating company_research_queries table: {e}")
        raise

def update_company_research_results(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> None:
    """Update the company_research_results table with data from the JSON file.
    
    Args:
        conn: DuckDB connection
        data: Dictionary containing company research data
    """
    try:
        if not data or 'company' not in data or 'research_results' not in data:
            logger.warning("No company or research results data found in the JSON file")
            return
        
        company = data['company']
        ticker = company.get('ticker')
        research_results = data.get('research_results', [])
        
        if not ticker:
            logger.warning("No ticker found in the company data")
            return
        
        if not research_results:
            logger.warning(f"No research results found for {ticker}")
            return
        
        # Delete existing results for this company
        conn.execute(f"DELETE FROM company_research_results WHERE company_ticker = '{ticker}'")
        
        # Insert new results
        for result in research_results:
            web_results = json.dumps(result.get('web_results', []))
            
            conn.execute("""
            INSERT INTO company_research_results (
                company_ticker, category, query, rationale, priority, web_results
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ticker,
                result.get('category'),
                result.get('query'),
                result.get('rationale'),
                result.get('priority'),
                web_results
            ])
        
        logger.info(f"Successfully updated company_research_results table for {ticker} with {len(research_results)} results")
    except Exception as e:
        logger.error(f"Error updating company_research_results table: {e}")
        raise

def process_directory(conn: duckdb.DuckDBPyConnection, directory_path: str) -> None:
    """Process all JSON files in a directory.
    
    Args:
        conn: DuckDB connection
        directory_path: Path to the directory containing JSON files
    """
    try:
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            logger.error(f"Directory does not exist or is not a directory: {directory_path}")
            return
        
        # Get all JSON files in the directory (excluding metadata files)
        json_files = [f for f in directory.glob("*.json") if not f.name.endswith(".metadata")]
        
        # Filter for research files
        research_files = [f for f in json_files if "_research.json" in f.name]
        
        if not research_files:
            logger.warning(f"No research JSON files found in {directory_path}")
            return
        
        logger.info(f"Found {len(research_files)} research JSON files in {directory_path}")
        
        for file_path in research_files:
            try:
                logger.info(f"Processing file: {file_path}")
                data = process_json_file(str(file_path))
                
                if data:
                    update_company_research(conn, data)
                    update_company_research_queries(conn, data)
                    update_company_research_results(conn, data)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
        
        logger.info(f"Completed processing {len(research_files)} research JSON files")
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {e}")
        raise

def main():
    """Main function to integrate JSON research files."""
    parser = argparse.ArgumentParser(description="Integrate company research information from JSON files")
    parser.add_argument("--database", default="dewey", help="MotherDuck database name")
    parser.add_argument("--input-dir", default="/Users/srvo/input_data/json_files", help="Directory containing input JSON files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Connect to MotherDuck
        conn = connect_to_motherduck(args.database)
        
        # Ensure tables exist
        ensure_tables_exist(conn)
        
        # Process JSON files
        process_directory(conn, args.input_dir)
        
        logger.info("JSON research integration completed successfully")
        
    except Exception as e:
        logger.error(f"Error in JSON research integration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 