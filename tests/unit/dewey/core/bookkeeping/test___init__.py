import pytest
from unittest.mock import patch, MagicMock
from dewey.core.bookkeeping import BookkeepingScript
from dewey.core.base_script import BaseScript
import logging


class TestBookkeepingScript:
    """Tests for the BookkeepingScript class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        with patch("dewey.core.bookkeeping.BaseScript", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def bookkeeping_script(self, mock_base_script: MagicMock) -> BookkeepingScript:
        """Creates an instance of BookkeepingScript with mocked dependencies."""
        return BookkeepingScript()

    def test_bookkeeping_script_initialization(
        self, mock_base_script: MagicMock
    ) -> None:
        """Tests the initialization of the BookkeepingScript class."""
        bookkeeping_script = BookkeepingScript()
        mock_base_script.assert_called_once_with(
            name="BookkeepingScript",
            description=bookkeeping_script.__doc__,
            config_section="bookkeeping",
            requires_db=True,
            enable_llm=False,
        )
        assert bookkeeping_script.config_section == "bookkeeping"

    def test_bookkeeping_script_initialization_with_custom_config(
        self, mock_base_script: MagicMock
    ) -> None:
        """Tests the initialization of BookkeepingScript with a custom config section."""
        config_section = "custom_bookkeeping"
        bookkeeping_script = BookkeepingScript(config_section=config_section)
        mock_base_script.assert_called_once_with(
            name="BookkeepingScript",
            description=bookkeeping_script.__doc__,
            config_section=config_section,
            requires_db=True,
            enable_llm=False,
        )
        assert bookkeeping_script.config_section == config_section

    def test_run_method_raises_not_implemented_error(
        self, bookkeeping_script: BookkeepingScript
    ) -> None:
        """Tests that the run method raises a NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="Subclasses must implement the run method."
        ):
            bookkeeping_script.run()

    def test_bookkeeping_script_inherits_from_base_script(
        self, bookkeeping_script: BookkeepingScript
    ) -> None:
        """Tests that BookkeepingScript inherits from BaseScript."""
        assert isinstance(bookkeeping_script, BaseScript)

    def test_bookkeeping_script_logging(
        self, bookkeeping_script: BookkeepingScript, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Tests that the BookkeepingScript logs initialization."""
        caplog.set_level(logging.INFO)
        BookkeepingScript()
        assert "Initialized BookkeepingScript" in caplog.text

    @patch("dewey.core.bookkeeping.load_dotenv")
    def test_bookkeeping_script_loads_dotenv(
        self, mock_load_dotenv: MagicMock, bookkeeping_script: BookkeepingScript
    ) -> None:
        """Tests that the BookkeepingScript loads the .env file."""
        mock_load_dotenv.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript._load_config")
    def test_bookkeeping_script_loads_config(
        self, mock_load_config: MagicMock, bookkeeping_script: BookkeepingScript
    ) -> None:
        """Tests that the BookkeepingScript loads the configuration."""
        bookkeeping_script = BookkeepingScript()
        mock_load_config.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript._initialize_db_connection")
    def test_bookkeeping_script_initializes_db_connection(
        self,
        mock_initialize_db_connection: MagicMock,
        bookkeeping_script: BookkeepingScript,
    ) -> None:
        """Tests that the BookkeepingScript initializes the database connection."""
        bookkeeping_script = BookkeepingScript()
        mock_initialize_db_connection.assert_called_once()

    @patch("dewey.core.bookkeeping.BaseScript._initialize_llm_client")
    def test_bookkeeping_script_does_not_initialize_llm_client(
        self,
        mock_initialize_llm_client: MagicMock,
        bookkeeping_script: BookkeepingScript,
    ) -> None:
        """Tests that the BookkeepingScript does not initialize the LLM client when enable_llm is False."""
        bookkeeping_script = BookkeepingScript()
        mock_initialize_llm_client.assert_not_called()

    @patch("dewey.core.bookkeeping.BaseScript._initialize_llm_client")
    def test_bookkeeping_script_initializes_llm_client_when_enabled(
        self, mock_initialize_llm_client: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Tests that the BookkeepingScript initializes the LLM client when enable_llm is True."""
        mock_base_script.return_value = None

        class MockBookkeepingScript(BookkeepingScript):
            """Class MockBookkeepingScript."""

            def __init__(self, config_section: str = "bookkeeping") -> None:
                """Function __init__."""
                super().__init__(config_section=config_section)
                self.enable_llm = True

            def run(self) -> None:
                """Function run."""
                pass

        bookkeeping_script = MockBookkeepingScript()
        bookkeeping_script._initialize_llm_client()
        mock_initialize_llm_client.assert_called_once()
