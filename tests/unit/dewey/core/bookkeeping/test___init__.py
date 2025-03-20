"""Tests for dewey.core.bookkeeping."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import logging
from typing import Dict, Any, Optional

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping import BookkeepingScript
from dewey.core.db.connection import DatabaseConnection


class TestBookkeepingScript:
    """Tests for the BookkeepingScript class."""

    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_initialization(
        self, mock_init: MagicMock
    ) -> None:
        """Tests the initialization of the BookkeepingScript class."""
        bookkeeping_script = BookkeepingScript()
        mock_init.assert_called_once_with(
            name="BookkeepingScript",
            description=bookkeeping_script.__doc__,
            config_section="bookkeeping",
            requires_db=True,
            enable_llm=False,
            db_connection=None,
        )
        assert bookkeeping_script.config_section == "bookkeeping"

    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_initialization_with_custom_config(
        self, mock_init: MagicMock
    ) -> None:
        """Tests the initialization of BookkeepingScript with a custom config section."""
        config_section = "custom_bookkeeping"
        bookkeeping_script = BookkeepingScript(config_section=config_section)
        mock_init.assert_called_once_with(
            name="BookkeepingScript",
            description=bookkeeping_script.__doc__,
            config_section=config_section,
            requires_db=True,
            enable_llm=False,
            db_connection=None,
        )
        assert bookkeeping_script.config_section == config_section

    def test_run_method_raises_not_implemented_error(self) -> None:
        """Tests that the run method raises a NotImplementedError."""
        with patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None):
            bookkeeping_script = BookkeepingScript()
            with pytest.raises(
                NotImplementedError, match="Subclasses must implement the run method."
            ):
                bookkeeping_script.run()

    def test_bookkeeping_script_inherits_from_base_script(self) -> None:
        """Tests that BookkeepingScript inherits from BaseScript."""
        with patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None):
            bookkeeping_script = BookkeepingScript()
            assert isinstance(bookkeeping_script, BaseScript)

    @patch("dewey.core.bookkeeping.BaseScript._setup_logging")
    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_logging(
        self, mock_init: MagicMock, mock_setup_logging: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Tests that the BookkeepingScript logs initialization."""
        caplog.set_level(logging.INFO)
        BookkeepingScript()
        assert "Initialized BookkeepingScript" in caplog.text

    @patch("dewey.core.bookkeeping.load_dotenv")
    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_loads_dotenv(
        self, mock_init: MagicMock, mock_load_dotenv: MagicMock
    ) -> None:
        """Tests that the BookkeepingScript loads the .env file."""
        BookkeepingScript()
        mock_load_dotenv.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript._load_config")
    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_loads_config(
        self, mock_init: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Tests that the BookkeepingScript loads the configuration."""
        BookkeepingScript()
        mock_load_config.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript._initialize_db_connection")
    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_initializes_db_connection(
        self,
        mock_init: MagicMock,
        mock_initialize_db_connection: MagicMock,
    ) -> None:
        """Tests that the BookkeepingScript initializes the database connection."""
        BookkeepingScript()
        mock_initialize_db_connection.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript._initialize_llm_client")
    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_does_not_initialize_llm_client(
        self,
        mock_init: MagicMock,
        mock_initialize_llm_client: MagicMock,
    ) -> None:
        """Tests that the BookkeepingScript does not initialize the LLM client when enable_llm is False."""
        BookkeepingScript()
        mock_initialize_llm_client.assert_not_called()

    @patch("dewey.core.bookkeeping.BaseScript._initialize_llm_client")
    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_initializes_llm_client_when_enabled(
        self, mock_init: MagicMock, mock_initialize_llm_client: MagicMock
    ) -> None:
        """Tests that the BookkeepingScript initializes the LLM client when enable_llm is True."""

        class MockBookkeepingScript(BookkeepingScript):
            """Class MockBookkeepingScript."""

            def __init__(self, config_section: str = "bookkeeping", db_connection: Optional[DatabaseConnection] = None) -> None:
                """Function __init__."""
                super().__init__(config_section=config_section, db_connection=db_connection)
                self.enable_llm = True

            def run(self) -> None:
                """Function run."""
                pass

        bookkeeping_script = MockBookkeepingScript()
        bookkeeping_script._initialize_llm_client()
        mock_initialize_llm_client.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript.__init__", return_value=None)
    def test_bookkeeping_script_initialization_with_db_connection(self, mock_init: MagicMock) -> None:
        """Tests the initialization of BookkeepingScript with a custom db_connection."""
        mock_db_connection = MagicMock(spec=DatabaseConnection)
        bookkeeping_script = BookkeepingScript(db_connection=mock_db_connection)
        mock_init.assert_called_once_with(
            name="BookkeepingScript",
            description=bookkeeping_script.__doc__,
            config_section="bookkeeping",
            requires_db=True,
            enable_llm=False,
            db_connection=mock_db_connection,
        )
        assert bookkeeping_script.db_connection == mock_db_connection
