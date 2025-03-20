import pytest
from unittest.mock import patch
from dewey.core.base_script import BaseScript
from dewey.core.crm.gmail.gmail_sync_manager import (
    GmailSyncManager,
)  # Assuming you will create this class


class TestGmailSyncManager:
    """Unit tests for the GmailSyncManager class."""

    @pytest.fixture
    def mock_base_script(self):
        """Fixture to mock BaseScript's methods."""
        with (
            patch.object(BaseScript, "_setup_logging") as mock_setup_logging,
            patch.object(BaseScript, "_load_config") as mock_load_config,
            patch.object(BaseScript, "_initialize_db_connection") as mock_init_db,
            patch.object(BaseScript, "_initialize_llm_client") as mock_init_llm,
        ):
            mock_load_config.return_value = {}  # Provide a default config
            yield mock_setup_logging, mock_load_config, mock_init_db, mock_init_llm

    def test_gmail_sync_manager_initialization(self, mock_base_script):
        """Test that GmailSyncManager initializes correctly."""
        mock_setup_logging, mock_load_config, mock_init_db, mock_init_llm = (
            mock_base_script
        )

        sync_manager = GmailSyncManager()

        assert isinstance(sync_manager, GmailSyncManager)
        assert isinstance(sync_manager, BaseScript)
        mock_setup_logging.assert_called_once()
        mock_load_config.assert_called_once()
        assert not mock_init_db.called
        assert not mock_init_llm.called

    def test_gmail_sync_manager_with_config_section(self, mock_base_script):
        """Test initialization with a config section."""
        mock_setup_logging, mock_load_config, mock_init_db, mock_init_llm = (
            mock_base_script
        )
        config_section = "gmail_sync"
        GmailSyncManager(config_section=config_section)
        assert mock_load_config.call_args[0][0] == config_section

    def test_gmail_sync_manager_requires_db(self, mock_base_script):
        """Test initialization with database requirement."""
        mock_setup_logging, mock_load_config, mock_init_db, mock_init_llm = (
            mock_base_script
        )
        GmailSyncManager(requires_db=True)
        assert mock_init_db.called

    def test_gmail_sync_manager_enables_llm(self, mock_base_script):
        """Test initialization with LLM enabled."""
        mock_setup_logging, mock_load_config, mock_init_db, mock_init_llm = (
            mock_base_script
        )
        GmailSyncManager(enable_llm=True)
        assert mock_init_llm.called

    def test_run_method_not_implemented(self):
        """Test that the run method raises NotImplementedError."""
        sync_manager = GmailSyncManager()
        with pytest.raises(TypeError):  # Changed from NotImplementedError to TypeError
            sync_manager.run()
