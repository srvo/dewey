import json
import logging
import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.bookkeeping.rules_converter import RulesConverter
from dewey.core.base_script import BaseScript

# Mocking PROJECT_ROOT and CONFIG_PATH for testing
PROJECT_ROOT = Path("/tmp/dewey_test")
CONFIG_PATH = PROJECT_ROOT / "config" / "dewey.yaml"


@pytest.fixture
def rules_converter() -> RulesConverter:
    """Fixture to create a RulesConverter instance with mocked config."""
    # Ensure the config directory exists
    (PROJECT_ROOT / "config").mkdir(parents=True, exist_ok=True)

    # Create a dummy config file
    dummy_config = {
        "core": {"logging": {"level": "DEBUG", "format": "%(message)s"}},
        "rules_converter": {"some_setting": "some_value"},
    }
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(dummy_config, f)

    # Patch the PROJECT_ROOT and CONFIG_PATH
    with patch("dewey.core.bookkeeping.rules_converter.PROJECT_ROOT", PROJECT_ROOT), patch(
        "dewey.core.bookkeeping.rules_converter.CONFIG_PATH", CONFIG_PATH
    ):
        converter = RulesConverter()
    return converter


def test_clean_category_expenses_draw(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:draw:all."""
    assert rules_converter.clean_category("expenses:draw:all") == "expenses:draw"


def test_clean_category_expenses_tech(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:tech:all."""
    assert rules_converter.clean_category("expenses:tech:all") == "expenses:software:subscription"


def test_clean_category_expenses_food(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:food:all."""
    assert rules_converter.clean_category("expenses:food:all") == "expenses:food:meals"


def test_clean_category_expenses_debt(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:debt:all."""
    assert rules_converter.clean_category("expenses:debt:all") == "expenses:financial:debt"


def test_clean_category_expenses_fees(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:fees:all."""
    assert rules_converter.clean_category("expenses:fees:all") == "expenses:financial:fees"


def test_clean_category_expenses_compliance(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:compliance:all."""
    assert (
        rules_converter.clean_category("expenses:compliance:all") == "expenses:professional:compliance"
    )


def test_clean_category_expenses_taxes(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:taxes:all."""
    assert rules_converter.clean_category("expenses:taxes:all") == "expenses:taxes"


def test_clean_category_expenses_insurance(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:insurance:all."""
    assert rules_converter.clean_category("expenses:insurance:all") == "expenses:insurance"


def test_clean_category_expenses_travel(rules_converter: RulesConverter) -> None:
    """Tests clean_category method for expenses:travel:all."""
    assert rules_converter.clean_category("expenses:travel:all") == "expenses:travel"


def test_clean_category_no_match(rules_converter: RulesConverter) -> None:
    """Tests clean_category method when no match is found."""
    assert rules_converter.clean_category("some:other:category") == "some:other:category"


def test_parse_rules_file_valid_rule(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests parse_rules_file method with a valid rule."""
    rules_file = tmp_path / "test_rules.rules"
    rules_file.write_text('if /test pattern/ then account2 "category>subcategory"')

    expected = {
        "test\\s+pattern": {
            "category": "category:subcategory", "examples": [], }
    }
    result = rules_converter.parse_rules_file(rules_file)
    assert result == expected


def test_parse_rules_file_empty_file(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests parse_rules_file method with an empty file."""
    rules_file=None, tmp_path: Path) -> None:
    """Tests parse_rules_file method with a comment line."""
    rules_file=None, tmp_path: Path) -> None:
    """Tests parse_rules_file method with an invalid regex pattern."""
    rules_file = tmp_path / "test_rules.rules"
    rules_file.write_text('if /(/ then account2 "category>subcategory"')

    with patch.object(rules_converter.logger, "exception") as mock_logger:
        result=None, tmp_path: Path) -> None:
    """Tests parse_rules_file method when no pattern is matched."""
    rules_file=None, tmp_path: Path) -> None:
    """Tests parse_rules_file method with category cleaning."""
    rules_file = tmp_path / "test_rules.rules"
    rules_file.write_text('if /pattern/ then account2 "expenses:draw:all"')
    result = rules_converter.parse_rules_file(rules_file)
    assert result["pattern"]["category"] == "expenses:draw"


def test_analyze_transactions_no_matches(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests analyze_transactions method when no transactions match the patterns."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    journal_file = journal_dir / "test.journal"
    journal_file.write_text("2023-01-01 Transaction 1\n  Account1\n  Account2")

    classifications: Dict[str, Dict[str, Any]] = {"pattern": {"category": "cat", "examples": []}}
    rules_converter.analyze_transactions(journal_dir, classifications)
    assert classifications["pattern"]["examples"]=None, tmp_path: Path) -> None:
    """Tests analyze_transactions method with a single matching transaction."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    journal_file = journal_dir / "test.journal"
    journal_file.write_text("2023-01-01 Test Transaction\n  Account1\n  Account2")

    classifications: Dict[str, Dict[str, Any]] = {
        "Test\\s+Transaction": {"category": "cat", "examples": []}
    }
    rules_converter.analyze_transactions(journal_dir, classifications)
    assert classifications["Test\\s+Transaction"]["examples"] == ["Test Transaction"]


def test_analyze_transactions_multiple_matches(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests analyze_transactions method with multiple matching transactions."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    journal_file = journal_dir / "test.journal"
    journal_file.write_text(
        "2023-01-01 Test Transaction\n  Account1\n  Account2\n"
        "2023-01-02 Another Test Transaction\n  Account1\n  Account2"
    )

    classifications: Dict[str, Dict[str, Any]] = {
        "Test\\s+Transaction": {"category": "cat", "examples": []}
    }
    rules_converter.analyze_transactions(journal_dir, classifications)
    assert classifications["Test\\s+Transaction"]["examples"] == ["Test Transaction", "Another Test Transaction"]


def test_analyze_transactions_existing_example(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests analyze_transactions method when the example already exists."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    journal_file = journal_dir / "test.journal"
    journal_file.write_text("2023-01-01 Test Transaction\n  Account1\n  Account2")

    classifications: Dict[str, Dict[str, Any]] = {
        "Test\\s+Transaction": {"category": "cat", "examples": ["Test Transaction"]}
    }
    rules_converter.analyze_transactions(journal_dir, classifications)
    assert classifications["Test\\s+Transaction"]["examples"] == ["Test Transaction"]


def test_generate_rules_json_empty_classifications(
    rules_converter: RulesConverter, tmp_path: Path
) -> None:
    """Tests generate_rules_json method with empty classifications."""
    output_file=None, output_file)

    with open(output_file, "r") as f:
        data=None, "categories": [], "stats": {"total_patterns": 0, "patterns_with_examples": 0}}


def test_generate_rules_json_single_classification(
    rules_converter: RulesConverter, tmp_path: Path
) -> None:
    """Tests generate_rules_json method with a single classification."""
    output_file = tmp_path / "rules.json"
    classifications: Dict[str, Dict[str, Any]] = {
        "pattern": {"category": "cat", "examples": ["example1", "example2"]}
    }
    rules_converter.generate_rules_json(classifications, output_file)

    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["patterns"]["pattern"]["category"] == "cat"
    assert data["patterns"]["pattern"]["examples"] == ["example1", "example2"]
    assert data["categories"] == ["cat"]
    assert data["stats"]["total_patterns"] == 1
    assert data["stats"]["patterns_with_examples"] == 1


def test_generate_rules_json_multiple_classifications(
    rules_converter: RulesConverter, tmp_path: Path
) -> None:
    """Tests generate_rules_json method with multiple classifications."""
    output_file = tmp_path / "rules.json"
    classifications: Dict[str, Dict[str, Any]] = {
        "pattern1": {"category": "cat1", "examples": ["example1"]}, "pattern2": {"category": "cat2", "examples": []}, }
    rules_converter.generate_rules_json(classifications, output_file)

    with open(output_file, "r") as f:
        data = json.load(f)

    assert set(data["categories"]) == {"cat1", "cat2"}
    assert data["stats"]["total_patterns"] == 2
    assert data["stats"]["patterns_with_examples"] == 1


def test_generate_rules_json_example_limit(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests generate_rules_json method with more than 5 examples."""
    output_file = tmp_path / "rules.json"
    classifications: Dict[str, Dict[str, Any]] = {
        "pattern": {"category": "cat", "examples": ["1", "2", "3", "4", "5", "6"]}
    }
    rules_converter.generate_rules_json(classifications, output_file)

    with open(output_file, "r") as f:
        data = json.load(f)

    assert len(data["patterns"]["pattern"]["examples"]) == 5
    assert data["patterns"]["pattern"]["examples"] == ["1", "2", "3", "4", "5"]


def test_run_method(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests the run method."""
    # Create dummy files and directories
    rules_file = tmp_path / "old_mercury.rules"
    rules_file.write_text('if /test pattern/ then account2 "category>subcategory"')
    journal_dir = tmp_path / "import" / "mercury" / "journal"
    journal_dir.mkdir(parents=True)
    journal_file = journal_dir / "test.journal"
    journal_file.write_text("2023-01-01 Test Transaction\n  Account1\n  Account2")
    output_file = tmp_path / "import" / "mercury" / "classification_rules.json"

    # Patch the file paths in the RulesConverter instance
    rules_converter.get_path = MagicMock(side_effect=lambda x: tmp_path / x)

    # Run the method
    rules_converter.run()

    # Assert that the output file was created
    assert output_file.exists()

    # Assert the contents of the output file
    with open(output_file, "r") as f:
        data = json.load(f)
    assert "patterns" in data
    assert "categories" in data
    assert "stats" in data


def test_main_function(rules_converter: RulesConverter, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Tests the main function."""
    # Create dummy files and directories
    rules_file = tmp_path / "old_mercury.rules"
    rules_file.write_text('if /test pattern/ then account2 "category>subcategory"')
    journal_dir = tmp_path / "import" / "mercury" / "journal"
    journal_dir.mkdir(parents=True)
    journal_file = journal_dir / "test.journal"
    journal_file.write_text("2023-01-01 Test Transaction\n  Account1\n  Account2")
    output_file = tmp_path / "import" / "mercury" / "classification_rules.json"

    # Patch the file paths in the RulesConverter instance
    rules_converter.get_path = MagicMock(side_effect=lambda x: tmp_path / x)

    # Patch the run method to avoid actually running the full process
    rules_converter.run = MagicMock()

    # Call the main function
    with patch("dewey.core.bookkeeping.rules_converter.RulesConverter", return_value=rules_converter):
if tmp_path: Path) -> None:
    """Tests parse_rules_file method with an empty file."""
    rules_file is None:
    tmp_path: Path) -> None:
    """Tests parse_rules_file method with an empty file."""
    rules_file = tmp_path / "test_rules.rules"
    rules_file.write_text("")
    assert rules_converter.parse_rules_file(rules_file) == {}


def test_parse_rules_file_comment_line(rules_converter: RulesConverter
if tmp_path: Path) -> None:
    """Tests parse_rules_file method with a comment line."""
    rules_file is None:
    tmp_path: Path) -> None:
    """Tests parse_rules_file method with a comment line."""
    rules_file = tmp_path / "test_rules.rules"
    rules_file.write_text("# This is a comment line")
    assert rules_converter.parse_rules_file(rules_file) == {}


def test_parse_rules_file_invalid_regex(rules_converter: RulesConverter
if "exception") as mock_logger:
        result is None:
    "exception") as mock_logger:
        result = rules_converter.parse_rules_file(rules_file)
        assert result == {}
        mock_logger.assert_called_once()


def test_parse_rules_file_no_pattern_match(rules_converter: RulesConverter
if tmp_path: Path) -> None:
    """Tests parse_rules_file method when no pattern is matched."""
    rules_file is None:
    tmp_path: Path) -> None:
    """Tests parse_rules_file method when no pattern is matched."""
    rules_file = tmp_path / "test_rules.rules"
    rules_file.write_text('if something then something_else "category>subcategory"')
    assert rules_converter.parse_rules_file(rules_file) == {}


def test_parse_rules_file_category_cleaning(rules_converter: RulesConverter
if classifications)
    assert classifications["pattern"]["examples"] is None:
    classifications)
    assert classifications["pattern"]["examples"] = = []


def test_analyze_transactions_single_match(rules_converter: RulesConverter
if tmp_path: Path
) -> None:
    """Tests generate_rules_json method with empty classifications."""
    output_file is None:
    tmp_path: Path
) -> None:
    """Tests generate_rules_json method with empty classifications."""
    output_file = tmp_path / "rules.json"
    rules_converter.generate_rules_json({}
if "r") as f:
        data is None:
    "r") as f:
        data = json.load(f)

    assert data == {"patterns": {}
from dewey.core.bookkeeping.rules_converter import main

        main()

    # Assert that the run method was called
    rules_converter.run.assert_called_once()


def test_logging_setup(tmp_path: Path) -> None:
    """Tests that logging is set up correctly."""
    # Create a dummy config file
    config_path = tmp_path / "dewey.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_config = {
        "core": {
            "logging": {
                "level": "DEBUG",
                "format": "%(levelname)s - %(name)s - %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
            }
        }
    }
    with open(config_path, "w") as f:
        yaml.dump(dummy_config, f)

    # Patch the PROJECT_ROOT and CONFIG_PATH
    with patch("dewey.core.bookkeeping.rules_converter.PROJECT_ROOT", tmp_path), patch(
        "dewey.core.bookkeeping.rules_converter.CONFIG_PATH", config_path
    ):
        script = RulesConverter()

    # Assert that the logger is set up correctly
    assert script.logger.level == logging.DEBUG
    assert script.logger.name == "RulesConverter"


def test_config_loading_with_section(tmp_path: Path) -> None:
    """Tests that the config is loaded correctly with a section."""
    # Create a dummy config file
    config_path = tmp_path / "dewey.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_config = {"rules_converter": {"setting1": "value1"}}
    with open(config_path, "w") as f:
        yaml.dump(dummy_config, f)

    # Patch the PROJECT_ROOT and CONFIG_PATH
    with patch("dewey.core.bookkeeping.rules_converter.PROJECT_ROOT", tmp_path), patch(
        "dewey.core.bookkeeping.rules_converter.CONFIG_PATH", config_path
    ):
        script = RulesConverter()

    # Assert that the config is loaded correctly
    assert script.config == {"setting1": "value1"}


def test_config_loading_no_section(tmp_path: Path) -> None:
    """Tests that the config is loaded correctly without a section."""
    # Create a dummy config file
    config_path = tmp_path / "dewey.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_config = {"setting1": "value1"}
    with open(config_path, "w") as f:
        yaml.dump(dummy_config, f)

    # Patch the PROJECT_ROOT and CONFIG_PATH
    with patch("dewey.core.bookkeeping.rules_converter.PROJECT_ROOT", tmp_path), patch(
        "dewey.core.bookkeeping.rules_converter.CONFIG_PATH", config_path
    ):
        script = BaseScript()

    # Assert that the config is loaded correctly
    assert script.config == {"setting1": "value1"}


def test_config_loading_file_not_found(tmp_path: Path) -> None:
    """Tests that the config loading raises an error when the file is not found."""
    # Patch the PROJECT_ROOT and CONFIG_PATH
    with patch("dewey.core.bookkeeping.rules_converter.PROJECT_ROOT", tmp_path), patch(
        "dewey.core.bookkeeping.rules_converter.CONFIG_PATH", tmp_path / "nonexistent.yaml"
    ), pytest.raises(FileNotFoundError):
        RulesConverter()


def test_config_loading_invalid_yaml(tmp_path: Path) -> None:
    """Tests that the config loading raises an error when the YAML is invalid."""
    # Create a dummy config file with invalid YAML
    config_path = tmp_path / "dewey.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("invalid yaml")

    # Patch the PROJECT_ROOT and CONFIG_PATH
    with patch("dewey.core.bookkeeping.rules_converter.PROJECT_ROOT", tmp_path), patch(
        "dewey.core.bookkeeping.rules_converter.CONFIG_PATH", config_path
    ), pytest.raises(yaml.YAMLError):
        RulesConverter()


def test_get_path_absolute(rules_converter: RulesConverter) -> None:
    """Tests get_path method with an absolute path."""
    absolute_path = "/absolute/path"
    assert rules_converter.get_path(absolute_path) == Path(absolute_path)


def test_get_path_relative(rules_converter: RulesConverter) -> None:
    """Tests get_path method with a relative path."""
    relative_path = "relative/path"
    expected_path = PROJECT_ROOT / relative_path
    assert rules_converter.get_path(relative_path) == expected_path


def test_get_config_value_existing_key(rules_converter: RulesConverter) -> None:
    """Tests get_config_value method with an existing key."""
    assert rules_converter.get_config_value("some_setting") == "some_value"


def test_get_config_value_nested_key(rules_converter: RulesConverter) -> None:
    """Tests get_config_value method with a nested key."""
    assert rules_converter.get_config_value("core.logging.level") == "DEBUG"


def test_get_config_value_default_value(rules_converter: RulesConverter) -> None:
    """Tests get_config_value method with a default value."""
    assert rules_converter.get_config_value("nonexistent_key", "default") == "default"


def test_get_config_value_nonexistent_key(rules_converter: RulesConverter) -> None:
    """Tests get_config_value method with a nonexistent key."""
    assert rules_converter.get_config_value("nonexistent_key") is None


def test_get_config_value_intermediate_key_missing(rules_converter: RulesConverter) -> None:
    """Tests get_config_value method when an intermediate key is missing."""
    assert rules_converter.get_config_value("core.nonexistent.level") is None


def test_setup_argparse(rules_converter: RulesConverter) -> None:
    """Tests the setup_argparse method."""
    parser = rules_converter.setup_argparse()
    assert parser.description == rules_converter.description
    assert parser.arguments[0].dest == "config"
    assert parser.arguments[1].dest == "log_level"


def test_parse_args_log_level(rules_converter: RulesConverter, caplog: pytest.LogCaptureFixture) -> None:
    """Tests the parse_args method with a log level."""
    with patch("sys.argv", ["script_name", "--log-level", "DEBUG"]):
        args = rules_converter.parse_args()
        assert args.log_level == "DEBUG"
        assert rules_converter.logger.level == logging.DEBUG
        assert "Log level set to DEBUG" in caplog.text


def test_parse_args_config_file(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests the parse_args method with a config file."""
    # Create a dummy config file
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("test_setting: test_value")

    with patch("sys.argv", ["script_name", "--config", str(config_file)]):
        args = rules_converter.parse_args()
        assert str(config_file) in str(args)
        assert rules_converter.config == {"test_setting": "test_value"}


def test_parse_args_config_file_not_found(rules_converter: RulesConverter, tmp_path: Path) -> None:
    """Tests the parse_args method with a config file that does not exist."""
    config_file = tmp_path / "nonexistent_config.yaml"

    with patch("sys.argv", ["script_name", "--config", str(config_file)]), pytest.raises(SystemExit) as exc_info:
        rules_converter.parse_args()

    assert exc_info.value.code == 1


def test_parse_args_db_connection_string(rules_converter: RulesConverter) -> None:
    """Tests the parse_args method with a database connection string."""
    rules_converter.requires_db = True
    with patch("sys.argv", ["script_name", "--db-connection-string", "test_connection_string"]):
        with patch("dewey.core.bookkeeping.rules_converter.get_connection") as mock_get_connection:
            args = rules_converter.parse_args()
            assert args.db_connection_string == "test_connection_string"
            mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
            assert rules_converter.db_conn == mock_get_connection.return_value


def test_parse_args_llm_model(rules_converter: RulesConverter) -> None:
    """Tests the parse_args method with an LLM model."""
    rules_converter.enable_llm = True
    with patch("sys.argv", ["script_name", "--llm-model", "test_llm_model"]):
        with patch("dewey.core.bookkeeping.rules_converter.get_llm_client") as mock_get_llm_client:
            args = rules_converter.parse_args()
            assert args.llm_model == "test_llm_model"
            mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
            assert rules_converter.llm_client == mock_get_llm_client.return_value


def test_execute_keyboard_interrupt(rules_converter: RulesConverter, caplog: pytest.LogCaptureFixture) -> None:
    """Tests the execute method with a KeyboardInterrupt."""
    rules_converter.parse_args = MagicMock(side_effect=KeyboardInterrupt)
    with pytest.raises(SystemExit) as exc_info:
        rules_converter.execute()
    assert exc_info.value.code == 1
    assert "Script interrupted by user" in caplog.text


def test_execute_exception(rules_converter: RulesConverter, caplog: pytest.LogCaptureFixture) -> None:
    """Tests the execute method with an exception."""
    rules_converter.parse_args = MagicMock()
    rules_converter.run = MagicMock(side_effect=Exception("Test exception"))
    with pytest.raises(SystemExit) as exc_info:
        rules_converter.execute()
    assert exc_info.value.code == 1
    assert "Error executing script: Test exception" in caplog.text


def test_execute_success(rules_converter: RulesConverter, caplog: pytest.LogCaptureFixture) -> None:
    """Tests the execute method with a successful run."""
    rules_converter.parse_args = MagicMock()
    rules_converter.run = MagicMock()
    rules_converter.execute()
    assert "Starting execution of RulesConverter" in caplog.text
    assert "Completed execution of RulesConverter" in caplog.text


def test_cleanup_db_connection(rules_converter: RulesConverter) -> None:
    """Tests the _cleanup method with a database connection."""
    rules_converter.db_conn = MagicMock()
    rules_converter._cleanup()
    rules_converter.db_conn.close.assert_called_once()


def test_cleanup_no_db_connection(rules_converter: RulesConverter) -> None:
    """Tests the _cleanup method without a database connection."""
    rules_converter.db_conn = None
    rules_converter._cleanup()
    # Assert that close is not called
    # rules_converter.db_conn.close.assert_not_called() # AttributeError: 'NoneType' object has no attribute 'close'
    pass
