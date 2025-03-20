import logging
from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml
from dotenv import load_dotenv

from dewey.core.base_script import BaseScript
from dewey.core.engines import EngineScript

# Constants for testing
TEST_CONFIG_PATH = Path(__file__).parent / "test_dewey.yaml"
TEST_LOG_PATH = Path(__file__).parent / "test_app.log"


# Fixtures
@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Fixture to load a test configuration file."""
    config_data = {
        "test_section": {
            "param1": "value1",
            "param2": 123,
        },
        "core": {
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
            }
        },
        "llm": {"model": "test_model"},
        "database": {"connection_string": "test_db_url"},
    }
    with open(TEST_CONFIG_PATH, "w") as f:
        yaml.dump(config_data, f)
    return config_data


@pytest.fixture
def mock_base_script(test_config: Dict[str, Any]) -> MagicMock:
    """Fixture to mock BaseScript class."""
    with patch("dewey.core.engines.BaseScript", autospec=True) as MockBaseScript:
        mock_instance = MockBaseScript.return_value
        mock_instance.config = test_config
        mock_instance.logger = MagicMock()
        yield mock_instance


# Test class for EngineScript
class TestEngineScript:
    """Test suite for the EngineScript class."""

    def test_engine_script_initialization_defaults(self) -> None:
        """Test EngineScript initialization with default values."""
        engine_script = EngineScript()
        assert engine_script.config_section is None
        assert engine_script.requires_db is False
        assert engine_script.enable_llm is False

    def test_engine_script_initialization_custom(self) -> None:
        """Test EngineScript initialization with custom values."""
        engine_script = EngineScript(
            config_section="test_section", requires_db=True, enable_llm=True
        )
        assert engine_script.config_section == "test_section"
        assert engine_script.requires_db is True
        assert engine_script.enable_llm is True

    def test_engine_script_inheritance(self) -> None:
        """Test that EngineScript inherits from BaseScript."""
        assert issubclass(EngineScript, BaseScript)

    def test_engine_script_abstract_run_method(self) -> None:
        """Test that EngineScript has an abstract run method."""

        class ConcreteEngineScript(EngineScript):
            def run(self) -> None:
                pass

        engine_script = ConcreteEngineScript()
        assert hasattr(engine_script, "run")
        assert callable(engine_script.run)

    def test_engine_script_initializes_base_script_correctly(
        self, test_config: Dict[str, Any]
    ) -> None:
        """Test that EngineScript initializes BaseScript with correct parameters."""
        with patch("dewey.core.base_script.BaseScript.__init__") as mock_base_init:
            EngineScript(
                config_section="test_section", requires_db=True, enable_llm=True
            )
            mock_base_init.assert_called_once_with(
                config_section="test_section", requires_db=True, enable_llm=True
            )

    def test_engine_script_run_raises_not_implemented_error(self) -> None:
        """Test that the abstract run method raises a NotImplementedError."""
        with pytest.raises(TypeError):
            EngineScript()

    def test_concrete_engine_script_run_does_not_raise_error(self) -> None:
        """Test that a concrete implementation of run does not raise an error."""

        class ConcreteEngineScript(EngineScript):
            def run(self) -> None:
                pass

        try:
            ConcreteEngineScript()
        except TypeError:
            pytest.fail("Concrete EngineScript raised TypeError")

    def test_engine_script_logging(self, test_config: Dict[str, Any]) -> None:
        """Test that EngineScript initializes logging correctly."""

        class ConcreteEngineScript(EngineScript):
            def run(self) -> None:
                self.logger.info("Test log message")

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            engine_script = ConcreteEngineScript()
            engine_script.run()
            mock_logger.info.assert_called_with("Test log message")

    def test_engine_script_config_loading(self, test_config: Dict[str, Any]) -> None:
        """Test that EngineScript loads configuration correctly."""

        class ConcreteEngineScript(EngineScript):
            def run(self) -> None:
                assert self.config == test_config

        engine_script = ConcreteEngineScript(config_section="test_section")
        engine_script.run()

    def test_engine_script_db_initialization(self, test_config: Dict[str, Any]) -> None:
        """Test that EngineScript initializes the database connection when required."""
        with patch("dewey.core.db.connection.get_connection") as mock_get_connection:

            class ConcreteEngineScript(EngineScript):
                def run(self) -> None:
                    pass

            engine_script = ConcreteEngineScript(requires_db=True)
            assert engine_script.db_conn is not None
            mock_get_connection.assert_called()

    def test_engine_script_llm_initialization(self, test_config: Dict[str, Any]) -> None:
        """Test that EngineScript initializes the LLM client when required."""
        with patch("dewey.llm.llm_utils.get_llm_client") as mock_get_llm_client:

            class ConcreteEngineScript(EngineScript):
                def run(self) -> None:
                    pass

            engine_script = ConcreteEngineScript(enable_llm=True)
            assert engine_script.llm_client is not None
            mock_get_llm_client.assert_called()

    def test_engine_script_initialization_exception_handling(self) -> None:
        """Test EngineScript initialization exception handling."""
        with patch(
            "dewey.core.base_script.BaseScript.__init__", side_effect=Exception("Test")
        ):
            with pytest.raises(Exception, match="Test"):
                EngineScript()

    def test_engine_script_config_section_not_found(self, test_config: Dict[str, Any]) -> None:
        """Test EngineScript when the config section is not found."""

        class ConcreteEngineScript(EngineScript):
            def run(self) -> None:
                assert self.config == test_config

        engine_script = ConcreteEngineScript(config_section="non_existent_section")
        engine_script.run()

    def test_engine_script_db_initialization_failure(self, test_config: Dict[str, Any]) -> None:
        """Test EngineScript database initialization failure."""
        with patch("dewey.core.db.connection.get_connection", side_effect=Exception("DB Error")):

            class ConcreteEngineScript(EngineScript):
                def run(self) -> None:
                    pass

            with pytest.raises(Exception, match="DB Error"):
                ConcreteEngineScript(requires_db=True)

    def test_engine_script_llm_initialization_failure(self, test_config: Dict[str, Any]) -> None:
        """Test EngineScript LLM initialization failure."""
        with patch("dewey.llm.llm_utils.get_llm_client", side_effect=Exception("LLM Error")):

            class ConcreteEngineScript(EngineScript):
                def run(self) -> None:
                    pass

            with pytest.raises(Exception, match="LLM Error"):
                ConcreteEngineScript(enable_llm=True)

    def teardown_method(self) -> None:
        """Teardown method to clean up resources after each test."""
        if TEST_CONFIG_PATH.exists():
            TEST_CONFIG_PATH.unlink()
        if TEST_LOG_PATH.exists():
            TEST_LOG_PATH.unlink()
