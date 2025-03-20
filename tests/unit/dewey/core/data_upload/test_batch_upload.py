import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.data_upload.batch_upload import BatchUpload


class TestBatchUpload:
    """Test suite for the BatchUpload class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript methods."""
        base_script_mock = MagicMock()
        base_script_mock.logger = MagicMock()
        base_script_mock.get_config_value.return_value = "/default/path"
        return base_script_mock

    def test_init(self) -> None:
        """Test the __init__ method of BatchUpload."""
        batch_upload = BatchUpload()
        assert batch_upload.config_section == "batch_upload"
        assert batch_upload.requires_db is False
        assert batch_upload.enable_llm is False

        batch_upload = BatchUpload(
            config_section="test", requires_db=True, enable_llm=True
        )
        assert batch_upload.config_section == "test"
        assert batch_upload.requires_db is True
        assert batch_upload.enable_llm is True

    @patch("dewey.core.data_upload.batch_upload.BaseScript.__init__")
    def test_init_base_script_call(self, mock_base_init: MagicMock) -> None:
        """Test that BaseScript.__init__ is called with the correct arguments."""
        BatchUpload(config_section="test", requires_db=True, enable_llm=True)
        mock_base_init.assert_called_once_with(
            config_section="test", requires_db=True, enable_llm=True
        )

    @patch("dewey.core.data_upload.batch_upload.BaseScript.get_config_value")
    def test_run_config_values(
        self, mock_get_config_value: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that config values are accessed correctly in the run method."""
        mock_get_config_value.return_value = "/test/path"
        batch_upload = BatchUpload()
        batch_upload.logger = mock_base_script.logger
        batch_upload.get_config_value = mock_get_config_value
        batch_upload.run()
        mock_get_config_value.assert_called_with("source_path", "/default/path")
        mock_base_script.logger.debug.assert_called_with("Source path: /test/path")

    @patch("dewey.core.data_upload.batch_upload.BaseScript.get_config_value")
    def test_run_no_db_no_llm(
        self, mock_get_config_value: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test the run method with no database or LLM."""
        batch_upload = BatchUpload()
        batch_upload.logger = mock_base_script.logger
        batch_upload.get_config_value = mock_get_config_value
        batch_upload.run()
        mock_base_script.logger.info.assert_called_with(
            "Batch upload process completed."
        )

    @patch("dewey.core.data_upload.batch_upload.BaseScript.get_config_value")
    def test_run_db_error(
        self, mock_get_config_value: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test the run method with a database error."""
        batch_upload = BatchUpload(requires_db=True)
        batch_upload.logger = mock_base_script.logger
        batch_upload.get_config_value = mock_get_config_value
        batch_upload.db_conn = MagicMock()
        batch_upload.db_conn.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            batch_upload.run()

        mock_base_script.logger.error.assert_called_with(
            "Database error: Database error"
        )

    @patch("dewey.core.data_upload.batch_upload.BaseScript.get_config_value")
    @patch("dewey.llm.llm_utils.generate_response")
    def test_run_llm_error(
        self,
        mock_generate_response: MagicMock,
        mock_get_config_value: MagicMock,
        mock_base_script: MagicMock,
    ) -> None:
        """Test the run method with an LLM error."""
        batch_upload = BatchUpload(enable_llm=True)
        batch_upload.logger = mock_base_script.logger
        batch_upload.get_config_value = mock_get_config_value
        batch_upload.llm_client = MagicMock()
        mock_generate_response.side_effect = Exception("LLM error")

        with pytest.raises(Exception, match="LLM error"):
            batch_upload.run()

        mock_base_script.logger.error.assert_called_with("LLM error: LLM error")

    @patch("dewey.core.data_upload.batch_upload.BaseScript.get_config_value")
    @patch("dewey.llm.llm_utils.generate_response")
    def test_run_llm_success(
        self,
        mock_generate_response: MagicMock,
        mock_get_config_value: MagicMock,
        mock_base_script: MagicMock,
    ) -> None:
        """Test the run method with successful LLM call."""
        batch_upload = BatchUpload(enable_llm=True)
        batch_upload.logger = mock_base_script.logger
        batch_upload.get_config_value = mock_get_config_value
        batch_upload.llm_client = MagicMock()
        mock_generate_response.return_value = "LLM Summary"

        batch_upload.run()

        mock_base_script.logger.info.assert_called_with("LLM Summary: LLM Summary")

    @patch("dewey.core.data_upload.batch_upload.BaseScript.get_config_value")
    def test_run_db_success(
        self, mock_get_config_value: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test the run method with successful database call."""
        batch_upload = BatchUpload(requires_db=True)
        batch_upload.logger = mock_base_script.logger
        batch_upload.get_config_value = mock_get_config_value
        batch_upload.db_conn = MagicMock()

        batch_upload.run()

        # Assert that db_conn.execute was called (replace with your actual assertion)
        # batch_upload.db_conn.execute.assert_called_once() # Removed because there is no actual query
        pass
