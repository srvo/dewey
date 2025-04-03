#!/usr/bin/env python3
"""JSON Research Integration Script
===============================

This script integrates company research information from JSON files into the MotherDuck database.
It processes JSON files containing company research data and updates the research tables.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

import duckdb

from dewey.core.base_script import BaseScript
from dewey.core.db import utils as db_utils


class JsonResearchIntegration(BaseScript):
    """Integrates company research information from JSON files into the MotherDuck database."""

    def __init__(self) -> None:
        """Initializes the JsonResearchIntegration script."""
        super().__init__(config_section="json_research_integration", requires_db=True)

    def connect_to_motherduck(
        self, database_name: str = "dewey"
    ) -> duckdb.DuckDBPyConnection:
        """Connect to the MotherDuck database.

        Args:
            database_name: Name of the MotherDuck database

        Returns:
            DuckDB connection

        Raises:
            Exception: If there is an error connecting to the database.

        """
        try:
            conn = duckdb.connect(f"md:{database_name}")
            self.logger.info(f"Connected to MotherDuck database: {database_name}")
            return conn
        except Exception as e:
            self.logger.error(f"Error connecting to MotherDuck database: {e}")
            raise

    def ensure_tales_exist(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Ensure that the necessary tables exist in the database.

        Args:
            conn: DuckDB connection

        Raises:
            Exception: If there is an error ensuring the tables exist.

        """
        try:
            # Check if company_research table exists
            if not db_utils.table_exists(conn, "company_research"):
                self.logger.info("Creating company_research table")
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
            if not db_utils.table_exists(conn, "company_research_queries"):
                self.logger.info("Creating company_research_queries table")
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
            if not db_utils.table_exists(conn, "company_research_results"):
                self.logger.info("Creating company_research_results table")
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

            self.logger.info("Tables verified/created successfully")
        except Exception as e:
            self.logger.error(f"Error ensuring tables exist: {e}")
            raise

    def process_json_file(self, file_path: str) -> Dict[str, Any]:
        """Process a JSON file containing company research data.

        Args:
            file_path: Path to the JSON file

        Returns:
            Dictionary containing the parsed JSON data

        Raises:
            Exception: If there is an error processing the JSON file.

        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.logger.error(f"Error processing JSON file {file_path}: {e}")
            raise

    def update_company_research(
        self, conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]
    ) -> None:
        """Update the company_research table with data from the JSON file.

        Args:
            conn: DuckDB connection
            data: Dictionary containing company research data

        Raises:
            Exception: If there is an error updating the company_research table.

        """
        try:
            if not data or "company" not in data:
                self.logger.warning("No company data found in the JSON file")
                return

            company = data["company"]
            ticker = company.get("ticker")

            if not ticker:
                self.logger.warning("No ticker found in the company data")
                return

            # Check if company already exists
            result = conn.execute(
                f"SELECT ticker FROM company_research WHERE ticker = '{ticker}'"
            ).fetchone()

            if result:
                # Update existing company
                self.logger.info(f"Updating existing company: {ticker}")
                conn.execute(
                    """
                UPDATE company_research SET
                    company_name = ?, description = ?, company_context = ?, updated_at = CURRENT_TIMESTAMP
                WHERE ticker = ?
                """,
                    [
                        company.get("name"),
                        company.get("description"),
                        data.get("company_context"),
                        ticker,
                    ],
                )
            else:
                # Insert new company
                self.logger.info(f"Inserting new company: {ticker}")
                conn.execute(
                    """
                INSERT INTO company_research (
                    ticker, company_name, description, company_context
                ) VALUES (?, ?, ?, ?)
                """,
                    [
                        ticker,
                        company.get("name"),
                        company.get("description"),
                        data.get("company_context"),
                    ],
                )

            self.logger.info(
                f"Successfully updated company_research table for {ticker}"
            )
        except Exception as e:
            self.logger.error(f"Error updating company_research table: {e}")
            raise

    def update_company_research_queries(
        self, conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]
    ) -> None:
        """Update the company_research_queries table with data from the JSON file.

        Args:
            conn: DuckDB connection
            data: Dictionary containing company research data

        Raises:
            Exception: If there is an error updating the company_research_queries table.

        """
        try:
            if not data or "company" not in data or "search_queries" not in data:
                self.logger.warning(
                    "No company or search queries data found in the JSON file"
                )
                return

            company = data["company"]
            ticker = company.get("ticker")
            search_queries = data.get("search_queries", [])

            if not ticker:
                self.logger.warning("No ticker found in the company data")
                return

            if not search_queries:
                self.logger.warning(f"No search queries found for {ticker}")
                return

            # Delete existing queries for this company
            conn.execute(
                f"DELETE FROM company_research_queries WHERE company_ticker = ?",
                [ticker],
            )

            # Insert new queries
            for query in search_queries:
                conn.execute(
                    """
                INSERT INTO company_research_queries (
                    company_ticker, category, query, rationale, priority
                ) VALUES (?, ?, ?, ?, ?)
                """,
                    [
                        ticker,
                        query.get("category"),
                        query.get("query"),
                        query.get("rationale"),
                        query.get("priority"),
                    ],
                )

            self.logger.info(
                f"Successfully updated company_research_queries table for {ticker} with {len(search_queries)} queries"
            )
        except Exception as e:
            self.logger.error(f"Error updating company_research_queries table: {e}")
            raise

    def update_company_research_results(
        self, conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]
    ) -> None:
        """Update the company_research_results table with data from the JSON file.

        Args:
            conn: DuckDB connection
            data: Dictionary containing company research data

        Raises:
            Exception: If there is an error updating the company_research_results table.

        """
        try:
            if not data or "company" not in data or "research_results" not in data:
                self.logger.warning(
                    "No company or research results data found in the JSON file"
                )
                return

            company = data["company"]
            ticker = company.get("ticker")
            research_results = data.get("research_results", [])

            if not ticker:
                self.logger.warning("No ticker found in the company data")
                return

            if not research_results:
                self.logger.warning(f"No research results found for {ticker}")
                return

            # Delete existing results for this company
            conn.execute(
                f"DELETE FROM company_research_results WHERE company_ticker = ?",
                [ticker],
            )

            # Insert new results
            for result in research_results:
                web_results = json.dumps(result.get("web_results", []))

                conn.execute(
                    """
                INSERT INTO company_research_results (
                    company_ticker, category, query, rationale, priority, web_results
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    [
                        ticker,
                        result.get("category"),
                        result.get("query"),
                        result.get("rationale"),
                        result.get("priority"),
                        web_results,
                    ],
                )

            self.logger.info(
                f"Successfully updated company_research_results table for {ticker} with {len(research_results)} results"
            )
        except Exception as e:
            self.logger.error(f"Error updating company_research_results table: {e}")
            raise

    def process_directory(
        self, conn: duckdb.DuckDBPyConnection, directory_path: str
    ) -> None:
        """Process all JSON files in a directory.

        Args:
            conn: DuckDB connection
            directory_path: Path to the directory containing JSON files

        Raises:
            Exception: If there is an error processing the directory.

        """
        try:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                self.logger.error(
                    f"Directory does not exist or is not a directory: {directory_path}"
                )
                return

            # Get all JSON files in the directory (excluding metadata files)
            json_files = [
                f for f in directory.glob("*.json") if not f.name.endswith(".metadata")
            ]

            # Filter for research files
            research_files = [f for f in json_files if "_research.json" in f.name]

            if not research_files:
                self.logger.warning(f"No research JSON files found in {directory_path}")
                return

            self.logger.info(
                f"Found {len(research_files)} research JSON files in {directory_path}"
            )

            for file_path in research_files:
                try:
                    self.logger.info(f"Processing file: {file_path}")
                    data = self.process_json_file(str(file_path))

                    if data:
                        self.update_company_research(conn, data)
                        self.update_company_research_queries(conn, data)
                        self.update_company_research_results(conn, data)
                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
                    continue

            self.logger.info(
                f"Completed processing {len(research_files)} research JSON files"
            )
        except Exception as e:
            self.logger.error(f"Error processing directory {directory_path}: {e}")
            raise

    def run(self) -> None:
        """Main function to integrate JSON research files."""
        database = self.get_config_value("database", "dewey")
        input_dir = self.get_config_value(
            "input_dir", "/Users/srvo/input_data/json_files"
        )

        try:
            # Connect to MotherDuck
            conn = self.connect_to_motherduck(database)

            # Ensure tables exist
            self.ensure_tables_exist(conn)

            # Process JSON files
            self.process_directory(conn, input_dir)

            self.logger.info("JSON research integration completed successfully")

        except Exception as e:
            self.logger.error(f"Error in JSON research integration: {e}")
            sys.exit(1)


def main():
    """Main entry point for the script."""
    script = JsonResearchIntegration()
    script.execute()


if __name__ == "__main__":
    main()
