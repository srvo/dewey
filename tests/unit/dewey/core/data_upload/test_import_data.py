import logging
from unittest.mock import MagicMock, patch
import pytest
from dewey.core.data_upload.import_data import ImportData


class TestImportData:
    """Unit tests for the ImportData class."""

    @pytest.fixture
    def mock_base_script(self):
        """Mocks the BaseScript class."""
        with patch(
            "dewey.core.data_upload.import_data.BaseScript", autospec=True
        ) as MockBaseScript:
            yield MockBaseScript

    @pytest.fixture
    def import_data(self, mock_base_script: MagicMock) -> ImportData:
        """Fixture to create an ImportData instance with mocked dependencies."""
        instance = ImportData()
        instance.logger = MagicMock(spec=logging.Logger)
        instance.get_config_value = MagicMock(return_value="test_source")
        instance.db_conn = MagicMock()
        return instance

    def test_init(self, mock_base_script: MagicMock) -> None:
        """Test the __init__ method of ImportData."""
        import_data = ImportData()
        mock_base_script.assert_called_once_with(
            config_section="import_data", requires_db=True, enable_llm=False
        )
        assert import_data.name == "ImportData"

    def test_run_success(self, import_data: ImportData) -> None:
        """Test the run method with a successful data import."""
        import_data.run()

        # Assert that the logger was called with the expected messages
        import_data.logger.info.assert_any_call("Starting ImportData script")
        import_data.logger.info.assert_any_call("Data source: test_source")
        import_data.logger.info.assert_any_call("ImportData script completed")

        # Assert that get_config_value was called with the correct arguments
        import_data.get_config_value.assert_called_with("data_source", "default_source")

    def test_run_exception(self, import_data: ImportData) -> None:
        """Test the run method when an exception occurs during data import."""
        # Configure the mock to raise an exception
        import_data.get_config_value.side_effect = Exception("Test exception")

        # Call the run method and assert that it raises an exception
        with pytest.raises(Exception, match="Test exception"):
            import_data.run()

        # Assert that the logger was called with the expected messages
        import_data.logger.info.assert_called_once_with("Starting ImportData script")
        import_data.logger.error.assert_called_once()

    @patch("dewey.core.data_upload.import_data.ImportData.execute")
    def test_main(self, mock_execute: MagicMock) -> None:
        """Test the main execution block."""
        # Patch the ImportData class to prevent actual instantiation
        with patch(
            "dewey.core.data_upload.import_data.ImportData", autospec=True
        ) as MockImportData:
            # Call the main execution block
            import_data = ImportData()
            import_data.execute()

            # Assert that ImportData was instantiated and execute was called
            MockImportData.assert_called_once()
            mock_execute.assert_called_once()
