"""Tests for CRM cataloger."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from dewey.core.crm.data_ingestion.crm_cataloger import CRMCataloger

class TestCRMCataloger:
    """Test suite for CRM cataloger."""

    @pytest.fixture
    def cataloger(self):
        """Create a CRMCataloger instance."""
        return CRMCataloger()

    def test_initialization(self, cataloger):
        """Test cataloger initialization."""
        assert cataloger.timestamp is not None
        assert cataloger.report_file.startswith("crm_catalog_")
        assert cataloger.report_file.endswith(".json")
        
        # Verify component definitions
        assert len(cataloger.components) > 0
        assert all(":" in comp for comp in cataloger.components)
        
        # Verify required environment variables
        assert "DB_URL" in cataloger.required_env_vars
        assert "ATTIO_API_KEY" in cataloger.required_env_vars
        assert "ONYX_API_KEY" in cataloger.required_env_vars

    def test_validate_component_definitions(self, cataloger):
        """Test validation of component definitions."""
        for component in cataloger.components:
            parts = component.split(":")
            assert len(parts) == 3  # filename:description::functions
            assert parts[0].endswith(".py")  # Valid Python file
            assert parts[1]  # Non-empty description
            assert parts[2]  # Has functions

    def test_check_environment_variables(self, cataloger):
        """Test environment variable checking."""
        with patch.dict('os.environ', {
            'DB_URL': 'test_url',
            'ATTIO_API_KEY': 'test_key',
            'ONYX_API_KEY': 'test_key'
        }):
            assert cataloger.check_environment_variables() is True
        
        with patch.dict('os.environ', {}, clear=True):
            assert cataloger.check_environment_variables() is False

    def test_validate_database_schema(self, cataloger, test_db):
        """Test database schema validation."""
        # Create required tables
        for table in cataloger.required_tables:
            test_db.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    contact_id VARCHAR PRIMARY KEY,
                    email_addresses VARCHAR,
                    search_results JSON
                )
            """)
        
        assert cataloger.validate_database_schema(test_db) is True
        
        # Drop a required table
        test_db.execute("DROP TABLE attio_contacts")
        assert cataloger.validate_database_schema(test_db) is False

    def test_check_dependencies(self, cataloger, tmp_path):
        """Test dependency checking."""
        # Create mock Python files
        for filename in cataloger.enrichment_deps.values():
            file_path = tmp_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("# Mock file")
        
        with patch('pathlib.Path.exists', return_value=True):
            assert cataloger.check_dependencies() is True
        
        with patch('pathlib.Path.exists', return_value=False):
            assert cataloger.check_dependencies() is False

    def test_collect_component_metrics(self, cataloger):
        """Test component metrics collection."""
        cataloger.collect_component_metrics()
        
        assert len(cataloger.component_metrics) > 0
        for component in cataloger.components:
            filename = component.split(":")[0]
            assert filename in cataloger.component_metrics
            
            metrics = cataloger.component_metrics[filename]
            assert "exists" in metrics
            assert "size" in metrics
            assert "last_modified" in metrics

    def test_generate_report(self, cataloger, tmp_path):
        """Test report generation."""
        report_file = tmp_path / "test_report.json"
        cataloger.report_file = str(report_file)
        
        # Generate report
        cataloger.generate_report()
        
        # Verify report was created
        assert report_file.exists()
        
        # Verify report content
        with open(report_file) as f:
            report = json.load(f)
            
        assert "timestamp" in report
        assert "components" in report
        assert "environment" in report
        assert "database" in report
        assert "dependencies" in report
        assert "metrics" in report

    def test_error_handling(self, cataloger):
        """Test error handling."""
        # Test with invalid component definition
        with pytest.raises(ValueError):
            cataloger.components.append("invalid_component")
            cataloger.validate_component_definitions()
        
        # Test with invalid database connection
        with pytest.raises(Exception):
            cataloger.validate_database_schema(None)

    @pytest.mark.integration
    def test_full_catalog_workflow(self, cataloger, test_db, tmp_path):
        """Integration test for full catalog workflow."""
        # Setup test environment
        env_vars = {
            'DB_URL': 'test_url',
            'ATTIO_API_KEY': 'test_key',
            'ONYX_API_KEY': 'test_key'
        }
        
        # Create required tables
        for table in cataloger.required_tables:
            test_db.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    contact_id VARCHAR PRIMARY KEY,
                    email_addresses VARCHAR,
                    search_results JSON
                )
            """)
        
        # Create mock dependency files
        for filename in cataloger.enrichment_deps.values():
            file_path = tmp_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("# Mock file")
        
        with patch.dict('os.environ', env_vars):
            with patch('pathlib.Path.exists', return_value=True):
                # Run full catalog workflow
                assert cataloger.check_environment_variables() is True
                assert cataloger.validate_database_schema(test_db) is True
                assert cataloger.check_dependencies() is True
                
                cataloger.collect_component_metrics()
                assert len(cataloger.component_metrics) > 0
                
                # Generate and verify report
                report_file = tmp_path / "catalog_report.json"
                cataloger.report_file = str(report_file)
                cataloger.generate_report()
                
                assert report_file.exists()
                with open(report_file) as f:
                    report = json.load(f)
                    assert all(key in report for key in [
                        "timestamp", "components", "environment",
                        "database", "dependencies", "metrics"
                    ]) 