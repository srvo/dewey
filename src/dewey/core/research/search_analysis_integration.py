#!/usr/bin/env python3
"""
Search Analysis Integration Script

This script processes search analysis JSON files and integrates the data into the MotherDuck database.
It handles company analysis data, including risk scores, key risks, and recommendations.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import duckdb
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/search_analysis_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
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
    """
    Ensure that the necessary tables exist in the database.
    
    Args:
        conn: DuckDB connection object
    """
    try:
        # Create search_analysis table if it doesn't exist
        conn.execute("""
        CREATE TABLE IF NOT EXISTS search_analysis (
            id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP,
            version VARCHAR,
            file_path VARCHAR,
            processed_at TIMESTAMP,
            metadata JSON
        )
        """)
        
        # Create company_analysis table if it doesn't exist
        conn.execute("""
        CREATE TABLE IF NOT EXISTS company_analysis (
            id VARCHAR PRIMARY KEY,
            search_analysis_id VARCHAR,
            company_name VARCHAR,
            symbol VARCHAR,
            risk_score INTEGER,
            confidence_score INTEGER,
            recommendation VARCHAR,
            processed_at TIMESTAMP,
            FOREIGN KEY (search_analysis_id) REFERENCES search_analysis(id)
        )
        """)
        
        # Create company_risk_factors table if it doesn't exist
        conn.execute("""
        CREATE TABLE IF NOT EXISTS company_risk_factors (
            id VARCHAR PRIMARY KEY,
            company_analysis_id VARCHAR,
            risk_type VARCHAR,
            description VARCHAR,
            FOREIGN KEY (company_analysis_id) REFERENCES company_analysis(id)
        )
        """)
        
        # Create company_evidence table if it doesn't exist
        conn.execute("""
        CREATE TABLE IF NOT EXISTS company_evidence (
            id VARCHAR PRIMARY KEY,
            company_analysis_id VARCHAR,
            url VARCHAR,
            title VARCHAR,
            snippet TEXT,
            domain VARCHAR,
            source_type VARCHAR,
            category VARCHAR,
            query_context VARCHAR,
            retrieved_at TIMESTAMP,
            published_date TIMESTAMP,
            source_hash VARCHAR,
            FOREIGN KEY (company_analysis_id) REFERENCES company_analysis(id)
        )
        """)
        
        logger.info("Successfully ensured all required tables exist")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise

def process_file(file_path: str, conn: duckdb.DuckDBPyConnection) -> None:
    """
    Process a single search analysis JSON file and update the database.
    
    Args:
        file_path: Path to the JSON file
        conn: DuckDB connection object
    """
    try:
        logger.info(f"Processing file: {file_path}")
        
        # Read the JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract metadata
        meta = data.get('meta', {})
        timestamp = meta.get('timestamp')
        version = meta.get('version')
        
        # Generate a unique ID for this analysis
        analysis_id = os.path.basename(file_path).replace('.json', '')
        
        # Insert into search_analysis table
        conn.execute("""
        INSERT OR REPLACE INTO search_analysis (id, timestamp, version, file_path, processed_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            analysis_id,
            timestamp,
            version,
            file_path,
            datetime.now(),
            json.dumps(meta)
        ))
        
        # Process each company in the analysis
        companies = data.get('companies', [])
        for company in companies:
            process_company(conn, analysis_id, company)
        
        logger.info(f"Successfully processed file: {file_path}")
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        raise

def process_company(conn: duckdb.DuckDBPyConnection, analysis_id: str, company: Dict[str, Any]) -> None:
    """
    Process a single company from the analysis and update the database.
    
    Args:
        conn: DuckDB connection object
        analysis_id: ID of the parent search analysis
        company: Company data dictionary
    """
    try:
        company_name = company.get('company_name', '')
        symbol = company.get('symbol', '')
        
        # Extract analysis data
        analysis_data = company.get('analysis', {})
        historical = analysis_data.get('historical', {})
        
        risk_score = historical.get('risk_score', 0)
        confidence_score = historical.get('confidence_score', 0)
        recommendation = historical.get('recommendation', '')
        
        # Generate a unique ID for this company analysis
        company_analysis_id = f"{analysis_id}_{symbol}"
        
        # Insert into company_analysis table
        conn.execute("""
        INSERT OR REPLACE INTO company_analysis (
            id, search_analysis_id, company_name, symbol, 
            risk_score, confidence_score, recommendation, processed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_analysis_id,
            analysis_id,
            company_name,
            symbol,
            risk_score,
            confidence_score,
            recommendation,
            datetime.now()
        ))
        
        # Process risk factors
        process_risk_factors(conn, company_analysis_id, historical)
        
        # Process evidence
        evidence = analysis_data.get('evidence', {})
        process_evidence(conn, company_analysis_id, evidence)
        
        logger.info(f"Successfully processed company: {company_name} ({symbol})")
    except Exception as e:
        logger.error(f"Error processing company {company.get('company_name', 'Unknown')}: {e}")
        raise

def process_risk_factors(conn: duckdb.DuckDBPyConnection, company_analysis_id: str, historical: Dict[str, Any]) -> None:
    """
    Process risk factors for a company and update the database.
    
    Args:
        conn: DuckDB connection object
        company_analysis_id: ID of the parent company analysis
        historical: Historical analysis data dictionary
    """
    try:
        # Delete existing risk factors for this company analysis
        conn.execute("""
        DELETE FROM company_risk_factors WHERE company_analysis_id = ?
        """, (company_analysis_id,))
        
        # Process key risks
        key_risks = historical.get('key_risks', [])
        for i, risk in enumerate(key_risks):
            conn.execute("""
            INSERT INTO company_risk_factors (id, company_analysis_id, risk_type, description)
            VALUES (?, ?, ?, ?)
            """, (
                f"{company_analysis_id}_key_{i}",
                company_analysis_id,
                'key_risk',
                risk
            ))
        
        # Process controversies
        controversies = historical.get('controversies', [])
        for i, controversy in enumerate(controversies):
            conn.execute("""
            INSERT INTO company_risk_factors (id, company_analysis_id, risk_type, description)
            VALUES (?, ?, ?, ?)
            """, (
                f"{company_analysis_id}_controversy_{i}",
                company_analysis_id,
                'controversy',
                controversy
            ))
        
        # Process environmental issues
        env_issues = historical.get('environmental_issues', [])
        for i, issue in enumerate(env_issues):
            conn.execute("""
            INSERT INTO company_risk_factors (id, company_analysis_id, risk_type, description)
            VALUES (?, ?, ?, ?)
            """, (
                f"{company_analysis_id}_env_{i}",
                company_analysis_id,
                'environmental',
                issue
            ))
        
        # Process social issues
        social_issues = historical.get('social_issues', [])
        for i, issue in enumerate(social_issues):
            conn.execute("""
            INSERT INTO company_risk_factors (id, company_analysis_id, risk_type, description)
            VALUES (?, ?, ?, ?)
            """, (
                f"{company_analysis_id}_social_{i}",
                company_analysis_id,
                'social',
                issue
            ))
        
        # Process governance issues
        gov_issues = historical.get('governance_issues', [])
        for i, issue in enumerate(gov_issues):
            conn.execute("""
            INSERT INTO company_risk_factors (id, company_analysis_id, risk_type, description)
            VALUES (?, ?, ?, ?)
            """, (
                f"{company_analysis_id}_gov_{i}",
                company_analysis_id,
                'governance',
                issue
            ))
        
        logger.info(f"Successfully processed risk factors for company analysis: {company_analysis_id}")
    except Exception as e:
        logger.error(f"Error processing risk factors for company analysis {company_analysis_id}: {e}")
        raise

def process_evidence(conn: duckdb.DuckDBPyConnection, company_analysis_id: str, evidence: Dict[str, Any]) -> None:
    """
    Process evidence sources for a company and update the database.
    
    Args:
        conn: DuckDB connection object
        company_analysis_id: ID of the parent company analysis
        evidence: Evidence data dictionary
    """
    try:
        # Delete existing evidence for this company analysis
        conn.execute("""
        DELETE FROM company_evidence WHERE company_analysis_id = ?
        """, (company_analysis_id,))
        
        # Process sources
        sources = evidence.get('sources', [])
        for i, source in enumerate(sources):
            conn.execute("""
            INSERT INTO company_evidence (
                id, company_analysis_id, url, title, snippet, domain, 
                source_type, category, query_context, retrieved_at, 
                published_date, source_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{company_analysis_id}_source_{i}",
                company_analysis_id,
                source.get('url', ''),
                source.get('title', ''),
                source.get('snippet', ''),
                source.get('domain', ''),
                source.get('source_type', ''),
                source.get('category', ''),
                source.get('query_context', ''),
                source.get('retrieved_at'),
                source.get('published_date'),
                source.get('source_hash', '')
            ))
        
        logger.info(f"Successfully processed evidence for company analysis: {company_analysis_id}")
    except Exception as e:
        logger.error(f"Error processing evidence for company analysis {company_analysis_id}: {e}")
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
        for file_name in json_files:
            if file_name.startswith('search_analysis_'):
                file_path = os.path.join(directory, file_name)
                process_file(file_path, conn)
        
        logger.info(f"Successfully processed {len(json_files)} files in directory: {directory}")
    except Exception as e:
        logger.error(f"Error processing directory {directory}: {e}")
        raise

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Process search analysis JSON files and update the database.')
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