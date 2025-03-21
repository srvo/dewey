"""Tests for the CRM data module."""

import os
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dewey.core.crm.data.data_importer import DataImporter


@pytest.fixture
def mock_csv_file() -> Generator[str, None, None]:
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
        # Create test data
        test_data = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["John Doe", "Jane Smith", "Bob Johnson"],
            "age": [30, 25, 40],
            "email": ["john@example.com", "jane@example.com", "bob@example.com"]
        })
        
        # Write to CSV
        test_data.to_csv(temp_file.name, index=False)
        
    # Return the file path
    yield temp_file.name
    
    # Clean up
    os.unlink(temp_file.name)


class TestDataImporter:
    """Test suite for DataImporter class."""
    
    def test_initialization(self) -> None:
        """Test DataImporter initialization."""
        importer = DataImporter()
        assert importer is not None
        assert importer.config_section == "data_importer"
        assert importer.requires_db is True
    
    def test_infer_csv_schema(self, mock_csv_file) -> None:
        """Test inferring CSV schema."""
        # Setup
        importer = DataImporter()
        
        # Execute
        schema = importer.infer_csv_schema(mock_csv_file)
        
        # Verify
        assert isinstance(schema, dict)
        assert "id" in schema
        assert "name" in schema
        assert "age" in schema
        assert "email" in schema
        assert schema["id"] == "INTEGER"
        assert schema["name"] == "VARCHAR"
        assert schema["age"] == "INTEGER"
        assert schema["email"] == "VARCHAR"
    
    @patch("dewey.core.db.connection.get_connection")
    def test_create_table_from_schema(self, mock_get_connection) -> None:
        """Test creating a table from a schema."""
        # Setup
        importer = DataImporter()
        mock_db = MagicMock()
        mock_get_connection.return_value = mock_db
        importer.db_conn = mock_db
        
        schema = {
            "id": "INTEGER",
            "name": "VARCHAR",
            "age": "INTEGER",
            "email": "VARCHAR"
        }
        
        # Execute
        importer.create_table_from_schema("test_table", schema, "id")
        
        # Verify
        mock_db.execute.assert_called_once()
        exec_args = mock_db.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS test_table" in exec_args
        assert '"id" INTEGER PRIMARY KEY' in exec_args
    
    @patch("dewey.core.db.connection.get_connection")
    def test_import_csv(self, mock_get_connection, mock_csv_file) -> None:
        """Test importing a CSV file."""
        # Setup
        importer = DataImporter()
        mock_db = MagicMock()
        mock_get_connection.return_value = mock_db
        importer.db_conn = mock_db
        
        # Mock infer_csv_schema and create_table_from_schema
        importer.infer_csv_schema = MagicMock(return_value={
            "id": "INTEGER",
            "name": "VARCHAR",
            "age": "INTEGER",
            "email": "VARCHAR"
        })
        importer.create_table_from_schema = MagicMock()
        
        # Execute
        rows_imported = importer.import_csv(mock_csv_file, "test_table", "id")
        
        # Verify
        importer.infer_csv_schema.assert_called_once_with(mock_csv_file)
        importer.create_table_from_schema.assert_called_once()
        assert mock_db.execute.call_count >= 3  # At least 3 inserts
        assert mock_db.commit.call_count >= 1
        assert rows_imported == 3
    
    @patch("dewey.core.db.connection.get_connection")
    def test_list_person_records(self, mock_get_connection) -> None:
        """Test listing person records."""
        # Setup
        importer = DataImporter()
        mock_db = MagicMock()
        mock_get_connection.return_value = mock_db
        importer.db_conn = mock_db
        
        # Mock fetchall() return value
        mock_db.execute.return_value.fetchall.return_value = [
            ("john@example.com", "John", "Doe", "John Doe", "ACME Inc.", "Developer", 
             "555-1234", "USA", "CSV", "example.com", "2023-01-01", "2023-01-01", 
             "2023-01-01", "tag1,tag2", "Test notes", "{}")
        ]
        
        # Mock description to provide column names
        mock_db.description = [
            ("email",), ("first_name",), ("last_name",), ("full_name",), 
            ("company",), ("job_title",), ("phone",), ("country",), 
            ("source",), ("domain",), ("last_interaction_date",), 
            ("first_seen_date",), ("last_updated",), ("tags",), 
            ("notes",), ("metadata",)
        ]
        
        # Execute
        persons = importer.list_person_records(10)
        
        # Verify
        mock_db.execute.assert_called_once()
        assert len(persons) == 1
        assert persons[0]["email"] == "john@example.com"
        assert persons[0]["first_name"] == "John"
        assert persons[0]["company"] == "ACME Inc."
    
    @patch("dewey.core.db.connection.get_connection")
    def test_run(self, mock_get_connection) -> None:
        """Test running the data import process."""
        # Setup
        importer = DataImporter()
        mock_db = MagicMock()
        mock_get_connection.return_value = mock_db
        importer.db_conn = mock_db
        
        # Mock config values
        importer.get_config_value = MagicMock(side_effect=lambda key, default=None: {
            "file_path": "/path/to/file.csv",
            "table_name": "test_table",
            "primary_key": "id"
        }.get(key, default))
        
        # Mock import_csv
        importer.import_csv = MagicMock(return_value=10)
        
        # Execute
        importer.run()
        
        # Verify
        importer.import_csv.assert_called_once_with("/path/to/file.csv", "test_table", "id") 