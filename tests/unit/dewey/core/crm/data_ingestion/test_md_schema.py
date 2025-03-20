import logging
from unittest.mock import patch

import pytest

from dewey.core.crm.data_ingestion.md_schema import MdSchema


class TestMdSchema:
    """Unit tests for the MdSchema class."""

    @pytest.fixture
    def md_schema(self, caplog):
        """Fixture to create an instance of MdSchema with a mock logger."""
        caplog.set_level(logging.INFO)  # Capture log messages for assertions
        return MdSchema()

    def test_init(self, md_schema):
        """Test the __init__ method of MdSchema."""
        assert md_schema.name == "MdSchema"
        assert md_schema.description is None
        assert md_schema.config_section is None
        assert md_schema.requires_db is False
        assert md_schema.enable_llm is False
        assert md_schema.logger is not None
        assert md_schema.config is not None
        assert md_schema.db_conn is None
        assert md_schema.llm_client is None

    def test_run_no_config(self, md_schema, caplog):
        """Test the run method of MdSchema with no specific config."""
        md_schema.run()
        assert "Running MD Schema module..." in caplog.text
        assert "Example config value: default_value" in caplog.text

    def test_run_with_config(self, md_schema, caplog):
        """Test the run method of MdSchema with a specific config section."""
        md_schema.config = {"md_schema": {"example_config_key": "test_value"}}
        md_schema.config_section = "md_schema"
        md_schema.run()
        assert "Running MD Schema module..." in caplog.text
        assert "Example config value: test_value" in caplog.text

    def test_get_config_value_existing(self, md_schema):
        """Test get_config_value when the key exists."""
        md_schema.config = {"section": {"key": "value"}}
        value = md_schema.get_config_value("section.key")
        assert value == "value"

    def test_get_config_value_default(self, md_schema):
        """Test get_config_value when the key does not exist and a default is provided."""
        md_schema.config = {"section": {}}
        value = md_schema.get_config_value("section.missing_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_missing_no_default(self, md_schema):
        """Test get_config_value when the key does not exist and no default is provided."""
        md_schema.config = {"section": {}}
        value = md_schema.get_config_value("section.missing_key")
        assert value is None

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args, md_schema, caplog):
        """Test parse_args updates log level."""
        mock_parse_args.return_value = pytest.Namespace(log_level="DEBUG", config=None)
        md_schema.parse_args()
        assert md_schema.logger.level == logging.DEBUG
        assert "Log level set to DEBUG" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_file(self, mock_parse_args, md_schema, tmp_path, caplog):
        """Test parse_args loads config from file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("test_key: test_value")
        mock_parse_args.return_value = pytest.Namespace(log_level=None, config=str(config_file))
        md_schema.parse_args()
        assert md_schema.config == {"test_key": "test_value"}
        assert f"Loaded configuration from {config_file}" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_file_not_found(self, mock_parse_args, md_schema, tmp_path, capsys):
        """Test parse_args handles config file not found."""
        config_file = tmp_path / "missing_config.yaml"
        mock_parse_args.return_value = pytest.Namespace(log_level=None, config=str(config_file))
        with pytest.raises(SystemExit) as excinfo:
            md_schema.parse_args()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Configuration file not found: {config_file}" in captured.err

    def test_get_path_absolute(self, md_schema, tmp_path):
        """Test get_path with an absolute path."""
        absolute_path = tmp_path / "test_file.txt"
        resolved_path = md_schema.get_path(str(absolute_path))
        assert resolved_path == absolute_path

    def test_get_path_relative(self, md_schema):
        """Test get_path with a relative path."""
        relative_path = "data/test_file.txt"
        resolved_path = md_schema.get_path(relative_path)
        expected_path = md_schema.PROJECT_ROOT / relative_path
        assert resolved_path == expected_path

    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema._cleanup")
    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema.parse_args")
    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema.run")
    def test_execute_success(self, mock_run, mock_parse_args, mock_cleanup, md_schema, caplog):
        """Test execute method for successful execution."""
        mock_parse_args.return_value = pytest.Namespace()
        md_schema.execute()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()
        assert f"Starting execution of {md_schema.name}" in caplog.text
        assert f"Completed execution of {md_schema.name}" in caplog.text

    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema._cleanup")
    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema.parse_args")
    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema.run")
    def test_execute_keyboard_interrupt(self, mock_run, mock_parse_args, mock_cleanup, md_schema, caplog, capsys):
        """Test execute method handles KeyboardInterrupt."""
        mock_parse_args.return_value = pytest.Namespace()
        mock_run.side_effect = KeyboardInterrupt
        with pytest.raises(SystemExit) as excinfo:
            md_schema.execute()
        assert excinfo.value.code == 1
        mock_cleanup.assert_called_once()
        assert "Script interrupted by user" in caplog.text

    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema._cleanup")
    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema.parse_args")
    @patch("dewey.core.crm.data_ingestion.md_schema.MdSchema.run")
    def test_execute_exception(self, mock_run, mock_parse_args, mock_cleanup, md_schema, caplog, capsys):
        """Test execute method handles exceptions."""
        mock_parse_args.return_value = pytest.Namespace()
        mock_run.side_effect = ValueError("Test error")
        with pytest.raises(SystemExit) as excinfo:
            md_schema.execute()
        assert excinfo.value.code == 1
        mock_cleanup.assert_called_once()
        assert "Error executing script: Test error" in caplog.text

    @patch("dewey.core.crm.data_ingestion.md_schema.BaseScript._initialize_db_connection")
    def test_init_requires_db(self, mock_init_db, caplog):
        """Test __init__ calls _initialize_db_connection when requires_db is True."""
        md_schema = MdSchema(requires_db=True)
        assert md_schema.requires_db is True
        mock_init_db.assert_called_once()

    @patch("dewey.core.crm.data_ingestion.md_schema.BaseScript._initialize_llm_client")
    def test_init_enable_llm(self, mock_init_llm, caplog):
        """Test __init__ calls _initialize_llm_client when enable_llm is True."""
        md_schema = MdSchema(enable_llm=True)
        assert md_schema.enable_llm is True
        mock_init_llm.assert_called_once()

    @patch("dewey.core.crm.data_ingestion.md_schema.BaseScript._cleanup")
    def test_cleanup_db_connection(self, mock_cleanup, md_schema):
        """Test _cleanup closes db connection if it exists."""
        md_schema.db_conn = pytest.mock.Mock()
        md_schema._cleanup()
        md_schema.db_conn.close.assert_called_once()

    @patch("dewey.core.crm.data_ingestion.md_schema.BaseScript._cleanup")
    def test_cleanup_no_db_connection(self, mock_cleanup, md_schema):
        """Test _cleanup does not try to close db connection if it doesn't exist."""
        md_schema.db_conn = None
        md_schema._cleanup()
        assert not hasattr(md_schema, 'close')
