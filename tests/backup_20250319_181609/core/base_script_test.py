import pytest
from pathlib import Path
from loguru import logger
from typing import Any, Optional
from unittest.mock import MagicMock
import os
from src.dewey.core.base_script import BaseScript, BaseScriptError, ExampleScript
from src.dewey.core.engines import MotherDuckEngine
from src.dewey.utils import get_logger
from src.dewey.llm.llm_utils import get_llm_client

@pytest.fixture
def tmp_log_dir(tmp_path):
    """Create temporary log directory fixture."""
    return tmp_path / "logs"

def test_base_script_initialization(tmp_log_dir):
    """Test BaseScript initializes with correct name/description/logger."""
    # Arrange
    name = "test_script"
    description = "Test description"
    os.environ["DEWEY_DIR"] = str(tmp_log_dir.parent)
    
    # Act
    script = BaseScript(name=name, description=description)
    
    # Assert
    assert script.name == name
    assert script.description == description
    assert script.logger.name == name
    assert script.logger.level == "DEBUG"  # Matches config from setup_test_environment
    assert (tmp_log_dir / "test_script.log").exists()

def test_setup_argparse_common_args():
    """Test common arguments (e.g. --debug) are added to parser."""
    # Arrange
    script = BaseScript()
    parser = script.setup_argparse()
    
    # Act
    args = parser.parse_args(["--debug"])
    
    # Assert
    assert args.debug is True

def test_validate_args_input_file_exists(tmp_path):
    """Test valid input file is accepted."""
    # Arrange
    input_file = tmp_path / "test.txt"
    input_file.touch()
    script = ExampleScript()
    parser = script.setup_argparse()
    args = parser.parse_args(["--input-file", str(input_file)])
    
    # Act/Assert
    script.validate_args(args)  # Should not raise

def test_validate_args_missing_input_file(tmp_path):
    """Test missing input file raises BaseScriptError."""
    # Arrange
    input_file = tmp_path / "missing.txt"
    script = ExampleScript()
    parser = script.setup_argparse()
    args = parser.parse_args(["--input-file", str(input_file)])
    
    # Act/Assert
    with pytest.raises(BaseScriptError, match=f"Input file not found: {input_file}"):
        script.validate_args(args)

def test_initialize_and_cleanup(tmp_path):
    """Test initialize() and cleanup() are called properly."""
    # Arrange
    class TestScript(BaseScript):
        initialized = False
        cleaned_up = False
        
        def initialize(self):
            self.initialized = True
        
        def cleanup(self):
            self.cleaned_up = True
    
    script = TestScript()
    
    # Act
    script.main()
    
    # Assert
    assert script.initialized is True
    assert script.cleaned_up is True

def test_main_error_handling(caplog):
    """Test main() handles exceptions and logs correctly."""
    # Arrange
    class ErrorScript(BaseScript):
        def run(self):
            raise ValueError("Test error")
    
    script = ErrorScript()
    
    # Act
    with pytest.raises(SystemExit) as exit_info:
        script.main()
    
    # Assert
    assert exit_info.value.code == 1
    assert "Unexpected error in errorscript: Test error" in caplog.text

def test_main_success_flow(caplog):
    """Test successful execution logs properly."""
    # Arrange
    script = ExampleScript()
    caplog.set_level("INFO")
    
    # Act
    script.main()
    
    # Assert
    assert "Starting example_script" in caplog.text
    assert "Completed example_script" in caplog.text
    assert "LLM response" in caplog.text
    assert "Database result" in caplog.text

def test_llm_client_property():
    """Test LLM client is lazily initialized."""
    # Arrange
    script = BaseScript()
    
    # Act
    client = script.llm_client
    
    # Assert
    assert client == get_llm_client()
    assert script._llm_client == client

def test_db_engine_property():
    """Test database engine is lazily initialized."""
    # Arrange
    script = BaseScript()
    
    # Act
    engine = script.db_engine
    
    # Assert
    assert isinstance(engine, MotherDuckEngine)
    assert script._db_engine == engine

def test_run_not_implemented():
    """Test run() raises NotImplementedError in base class."""
    # Arrange
    script = BaseScript()
    
    # Act/Assert
    with pytest.raises(NotImplementedError):
        script.run()

@pytest.fixture
def test_db(tmp_path):
    """Provide temporary DuckDB database connection."""
    db_path = tmp_path / "test.duckdb"
    engine = MotherDuckEngine(db_path=str(db_path))
    engine.execute("CREATE TABLE test (id INTEGER)")
    yield engine
    engine.close()

def test_ibis_query(test_db):
    """Test Ibis integration with BaseScript's database."""
    # Arrange
    script = BaseScript()
    table = script.db_engine.ibis_table("test")
    
    # Act
    result = table.execute()
    
    # Assert
    assert len(result) == 0  # Empty table as expected

def test_database_execution(tmp_path):
    """Test database execution through BaseScript."""
    # Arrange
    script = BaseScript()
    test_query = "SELECT 'test' AS result"
    
    # Act
    result = script.db_engine.execute(test_query)
    
    # Assert
    assert result[0]["result"] == "test"

def test_uses_central_config(tmp_path):
    """Test logging config is loaded from central config file."""
    # Arrange
    script = BaseScript()
    
    # Assert
    assert script.logger.level == "DEBUG"
    assert script.logger.handlers[0].formatter._fmt == "[%(levelname)s] %(message)s"

def test_all_required_methods_implemented():
    """Test BaseScript subclass must implement run()."""
    # Arrange
    class InvalidScript(BaseScript):
        pass  # Missing required run() method
    
    # Act/Assert
    with pytest.raises(TypeError, match="__init__"):
        InvalidScript()

def test_logging_configuration():
    """Test logging format matches config."""
    # Arrange
    script = BaseScript()
    
    # Assert
    handler = script.logger.handlers[0]
    assert handler.formatter._fmt == "[%(levelname)s] %(message)s"

def test_final_test_lifecycle(caplog):
    """Test end-to-end script lifecycle."""
    # Arrange
    script = ExampleScript()
    caplog.set_level("DEBUG")
    
    # Act
    script.main()
    
    # Assert
    assert "Starting example_script" in caplog.text
    assert "Completed example_script" in caplog.text
    assert "LLM response" in caplog.text
    assert "Database result" in caplog.text
