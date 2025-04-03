"""Data Importer Module for CRM

This module provides functionality for importing data from various sources
into the CRM system, with a focus on CSV files and other structured data formats.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from dewey.core.base_script import BaseScript


class DataImporter(BaseScript):
    """A class for importing data from various sources into the CRM system.

    This class provides methods for importing data from CSV files and other
    structured data formats, inferring schemas, and handling data validation.
    """

    def __init__(self) -> None:
        """Initialize the DataImporter."""
        super().__init__(config_section="data_importer", requires_db=True)

    def infer_csv_schema(self, file_path: str) -> dict[str, str]:
        """Infer the schema of a CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            A dictionary mapping column names to inferred data types

        """
        try:
            self.logger.info(f"Inferring schema for CSV file: {file_path}")

            # Read the first few rows to infer schema
            df = pd.read_csv(file_path, nrows=100)

            # Initialize schema
            schema = {}

            # Infer data types for each column
            for column in df.columns:
                # Get the pandas dtype
                pd_dtype = df[column].dtype

                # Map pandas dtype to SQL type
                if pd.api.types.is_integer_dtype(pd_dtype):
                    sql_type = "INTEGER"
                elif pd.api.types.is_float_dtype(pd_dtype):
                    sql_type = "REAL"
                elif pd.api.types.is_datetime64_dtype(pd_dtype):
                    sql_type = "TIMESTAMP"
                elif pd.api.types.is_bool_dtype(pd_dtype):
                    sql_type = "BOOLEAN"
                else:
                    # Default to VARCHAR for strings and other types
                    sql_type = "VARCHAR"

                schema[column] = sql_type

            self.logger.info(f"Inferred schema with {len(schema)} columns")
            return schema

        except Exception as e:
            self.logger.error(f"Error inferring CSV schema: {e}")
            raise

    def create_table_from_schema(
        self, table_name: str, schema: dict[str, str], primary_key: str | None = None
    ) -> None:
        """Create a database table from a schema.

        Args:
            table_name: Name of the table to create
            schema: Schema dictionary mapping column names to data types
            primary_key: Optional primary key column

        Returns:
            None

        """
        try:
            if not self.db_conn:
                raise RuntimeError("No database connection available")

            # Build CREATE TABLE SQL
            columns_sql = []
            for column, data_type in schema.items():
                column_def = f'"{column}" {data_type}'
                if primary_key and column == primary_key:
                    column_def += " PRIMARY KEY"
                columns_sql.append(column_def)

            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {", ".join(columns_sql)}
            )
            """

            # Execute the SQL
            self.db_conn.execute(create_sql)
            self.logger.info(f"Created or verified table: {table_name}")

        except Exception as e:
            self.logger.error(f"Error creating table from schema: {e}")
            raise

    def import_csv(
        self,
        file_path: str,
        table_name: str,
        primary_key: str | None = None,
        batch_size: int = 1000,
    ) -> int:
        """Import a CSV file into a database table.

        Args:
            file_path: Path to the CSV file
            table_name: Name of the table to import into
            primary_key: Optional primary key column
            batch_size: Number of rows to import in each batch

        Returns:
            Number of rows imported

        """
        try:
            self.logger.info(f"Importing CSV file: {file_path} to table: {table_name}")

            # Infer schema
            schema = self.infer_csv_schema(file_path)

            # Create table
            self.create_table_from_schema(table_name, schema, primary_key)

            # Read the CSV file in chunks
            df_iterator = pd.read_csv(file_path, chunksize=batch_size)

            # Track total rows imported
            total_rows = 0

            # Process each chunk
            for chunk_index, chunk in enumerate(df_iterator):
                # Convert chunk to records
                records = chunk.to_dict(orient="records")

                if records:
                    # Create placeholders for SQL
                    placeholders = ", ".join(["?"] * len(schema))
                    columns = ", ".join([f'"{col}"' for col in schema.keys()])

                    # Create INSERT statement
                    insert_sql = f"""
                    INSERT OR IGNORE INTO {table_name} ({columns})
                    VALUES ({placeholders})
                    """

                    # Insert records
                    for record in records:
                        values = [record.get(col, None) for col in schema.keys()]
                        self.db_conn.execute(insert_sql, values)

                    self.db_conn.commit()

                    # Update total
                    total_rows += len(records)
                    self.logger.info(
                        f"Imported chunk {chunk_index + 1} with {len(records)} rows"
                    )

            self.logger.info(f"Import completed. Total rows imported: {total_rows}")
            return total_rows

        except Exception as e:
            self.logger.error(f"Error importing CSV file: {e}")
            raise

    def list_person_records(self, limit: int = 100) -> list[dict[str, Any]]:
        """List person records from the CRM system.

        Args:
            limit: Maximum number of records to return

        Returns:
            A list of person dictionaries

        """
        try:
            if not self.db_conn:
                raise RuntimeError("No database connection available")

            # Query unified_contacts table (created by ContactConsolidation)
            result = self.db_conn.execute(f"""
            SELECT * FROM unified_contacts
            LIMIT {limit}
            """).fetchall()

            # Convert to list of dictionaries
            columns = [desc[0] for desc in self.db_conn.description]
            persons = []

            for row in result:
                person = {columns[i]: value for i, value in enumerate(row)}
                persons.append(person)

            self.logger.info(f"Retrieved {len(persons)} person records")
            return persons

        except Exception as e:
            self.logger.error(f"Error listing person records: {e}")
            return []

    def execute(self) -> None:
        """Execute the data import process.

        This method orchestrates the data import process by reading
        configuration values and importing data from the specified source.
        """
        self.logger.info("Starting data import process")

        try:
            # Get import parameters from config
            file_path = self.get_config_value("file_path")
            table_name = self.get_config_value("table_name")
            primary_key = self.get_config_value("primary_key", None)

            if not file_path:
                raise ValueError("Missing file_path in configuration")

            if not table_name:
                # Use filename as table name if not specified
                table_name = Path(file_path).stem.lower().replace(" ", "_")

            # Import the data
            rows_imported = self.import_csv(file_path, table_name, primary_key)

            self.logger.info(
                f"Data import completed. Imported {rows_imported} rows to {table_name}"
            )

        except Exception as e:
            self.logger.error(f"Error during data import: {e}")
            raise


if __name__ == "__main__":
    importer = DataImporter()
    importer.run()
