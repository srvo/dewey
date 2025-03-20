"""Tests for dewey.core.bookkeeping.classification_engine module."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest

from dewey.core.bookkeeping.classification_engine import (
    ClassificationEngine,
    ClassificationError,
)


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_classification_engine_initialization(mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path) -> None:
    """Test ClassificationEngine initialization."""
    assert classification_engine.ledger_file == tmp_path / "ledger.txt"
    assert classification_engine.rules_path.exists()
    assert isinstance(classification_engine.rules, dict)
    assert isinstance(classification_engine.compiled_patterns, dict)


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_categories_property(mock_base_script, classification_engine: ClassificationEngine) -> None:
    """Test the categories property."""
    assert classification_engine.categories == [
        "category1",
        "category2",
        "expenses:unknown",
        "income:unknown",
    ]


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("builtins.open", new_callable=mock_open, read_data='{"patterns": {}, "categories": [], "defaults": {"positive": "income:unknown", "negative": "expenses:unknown"}, "overrides": {}, "sources": []}')
@patch("json.load")
def test_load_rules(mock_json_load, mock_open_file, mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any], tmp_path: Path) -> None:
    """Test loading rules from a JSON file."""
    mock_json_load.return_value = rules_data
    rules = classification_engine._load_rules()
    assert rules["patterns"] == rules_data["patterns"]
    assert rules["categories"] == rules_data["categories"]
    assert rules["defaults"] == rules_data["defaults"]
    assert rules["overrides"] == rules_data["overrides"]


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", side_effect=FileNotFoundError)
def test_load_rules_file_not_found(mock_open_file, mock_exists, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path, caplog) -> None:
    """Test loading rules when the file is not found."""
    caplog.set_level(logging.ERROR)
    mock_exists.return_value = False
    classification_engine.rules_path = tmp_path / "nonexistent_rules.json"
    rules = classification_engine._load_rules()
    assert rules["patterns"] == {}
    assert "Failed to load classification rules" in caplog.text


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
@patch("json.load", side_effect=json.JSONDecodeError("", "", 0))
def test_load_rules_invalid_json(mock_json_load, mock_open_file, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path, caplog) -> None:
    """Test loading rules from an invalid JSON file."""
    caplog.set_level(logging.ERROR)
    rules_path = tmp_path / "invalid_rules.json"
    classification_engine.rules_path = rules_path
    rules = classification_engine._load_rules()
    assert rules["patterns"] == {}
    assert "Failed to load classification rules" in caplog.text


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_compile_patterns(mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any]) -> None:
    """Test compiling regex patterns."""
    classification_engine.rules = rules_data
    compiled_patterns = classification_engine._compile_patterns()
    assert isinstance(compiled_patterns, dict)
    assert all(isinstance(p, re.Pattern) for p in compiled_patterns.values())


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_compile_patterns_invalid_regex(mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any], caplog) -> None:
    """Test compiling regex patterns with an invalid regex."""
    caplog.set_level(logging.ERROR)
    rules_data["patterns"]["invalid_pattern"] = "["
    classification_engine.rules = rules_data
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._compile_patterns()
    assert "Invalid regex pattern" in str(exc_info.value)
    assert "Invalid regex pattern" in caplog.text


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_classify(mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any]) -> None:
    """Test classifying a transaction."""
    classification_engine.rules = rules_data
    classification_engine.compiled_patterns = classification_engine._compile_patterns()
    income_account, expense_account, amount = classification_engine.classify(
        description="pattern1 transaction", amount=100.0
    )
    assert income_account == "income:unknown"
    assert expense_account == "category1"
    assert amount == 100.0

    income_account, expense_account, amount = classification_engine.classify(
        description="pattern2 transaction", amount=-50.0
    )
    assert income_account == "category2"
    assert expense_account == "expenses:unknown"
    assert amount == 50.0


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_classify_no_match(mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any]) -> None:
    """Test classifying a transaction with no matching pattern."""
    classification_engine.rules = rules_data
    classification_engine.compiled_patterns = classification_engine._compile_patterns()
    income_account, expense_account, amount = classification_engine.classify(
        description="unmatched transaction", amount=75.0
    )
    assert income_account == "income:unknown"
    assert expense_account == "income:unknown"
    assert amount == 75.0

    income_account, expense_account, amount = classification_engine.classify(
        description="unmatched transaction", amount=-25.0
    )
    assert income_account == "expenses:unknown"
    assert expense_account == "expenses:unknown"
    assert amount == 25.0


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("dewey.core.bookkeeping.classification_engine.ClassificationEngine._save_overrides")
@patch("dewey.core.bookkeeping.classification_engine.ClassificationEngine._compile_patterns")
def test_process_feedback(mock_compile_patterns, mock_save_overrides, mock_base_script, classification_engine: ClassificationEngine, mock_journal_writer: MagicMock, rules_data: Dict[str, Any]) -> None:
    """Test processing user feedback."""
    classification_engine.rules = rules_data
    feedback = 'Classify "new transaction" as new_category'
    classification_engine.process_feedback(feedback, mock_journal_writer)
    assert "new transaction" in classification_engine.rules["overrides"]
    assert classification_engine.rules["overrides"]["new transaction"]["category"] == "new_category"
    mock_journal_writer.log_classification_decision.assert_called_once()
    mock_save_overrides.assert_called_once()
    mock_compile_patterns.assert_called_once()


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_process_feedback_invalid_category(mock_base_script, classification_engine: ClassificationEngine, mock_journal_writer: MagicMock, rules_data: Dict[str, Any]) -> None:
    """Test processing user feedback with an invalid category."""
    classification_engine.rules = rules_data
    feedback = 'Classify "new transaction" as invalid_category'
    with pytest.raises(ValueError) as exc_info:
        classification_engine.process_feedback(feedback, mock_journal_writer)
    assert "is not an allowed category" in str(exc_info.value)


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_parse_feedback(mock_base_script, classification_engine: ClassificationEngine) -> None:
    """Test parsing user feedback."""
    feedback = 'Classify "test transaction" as test_category'
    pattern, category = classification_engine._parse_feedback(feedback)
    assert pattern == "test transaction"
    assert category == "test_category"


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_parse_feedback_invalid_format(mock_base_script, classification_engine: ClassificationEngine) -> None:
    """Test parsing user feedback with an invalid format."""
    feedback = "invalid feedback"
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._parse_feedback(feedback)
    assert "Invalid feedback format" in str(exc_info.value)


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("dewey.core.bookkeeping.classification_engine.llm_utils.call_llm")
def test_parse_with_ai(
    mock_call_llm: MagicMock, mock_base_script, classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI."""
    mock_call_llm.return_value = [{"example": '{"pattern": "ai pattern", "category": "ai_category"}'}]
    feedback = "complex feedback"
    pattern, category = classification_engine._parse_with_ai(feedback)
    assert pattern == "ai pattern"
    assert category == "ai_category"
    mock_call_llm.assert_called_once()


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("dewey.core.bookkeeping.classification_engine.llm_utils.call_llm")
def test_parse_with_ai_no_response(
    mock_call_llm: MagicMock, mock_base_script, classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI when there is no response."""
    mock_call_llm.return_value = []
    feedback = "complex feedback"
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._parse_with_ai(feedback)
    assert "No response from AI" in str(exc_info.value)
    mock_call_llm.assert_called_once()


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("dewey.core.bookkeeping.classification_engine.llm_utils.call_llm")
def test_parse_with_ai_parsing_fails(
    mock_call_llm: MagicMock, mock_base_script, classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI when parsing fails."""
    mock_call_llm.return_value = [{"example": "invalid json"}]
    feedback = "complex feedback"
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._parse_with_ai(feedback)
    assert "AI parsing failed" in str(exc_info.value)
    mock_call_llm.assert_called_once()


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_save_overrides(mock_json_dump, mock_open_file, mock_path_exists, mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any], tmp_path: Path) -> None:
    """Test saving override rules to file."""
    mock_path_exists.return_value = True
    overrides_file = tmp_path.parent / "src" / "dewey" / "core" / "rules" / "overrides.json"
    overrides_file.parent.mkdir(parents=True, exist_ok=True)
    classification_engine.rules = rules_data
    classification_engine.rules["overrides"] = {"pattern1": {"category": "category1"}}
    classification_engine._save_overrides()
    mock_open_file.assert_called()
    mock_json_dump.assert_called()


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_validate_category(mock_base_script, classification_engine: ClassificationEngine, rules_data: Dict[str, Any]) -> None:
    """Test validating a category."""
    classification_engine.rules = rules_data
    classification_engine._valid_categories = rules_data["categories"]
    classification_engine._validate_category("category1")  # Valid category
    with pytest.raises(ValueError) as exc_info:
        classification_engine._validate_category("invalid_category")
    assert "is not an allowed category" in str(exc_info.value)


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("json.load")
def test_load_prioritized_rules(mock_json_load, mock_open_file, mock_path_exists, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path) -> None:
    """Test loading prioritized rules from multiple sources."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Create mock rule files
    base_rules_path = rules_dir / "base_rules.json"
    manual_rules_path = rules_dir / "manual_rules.json"
    overrides_rules_path = rules_dir / "overrides.json"

    base_rules_data = {"patterns": {"base_pattern": {"category": "base_category"}}}
    manual_rules_data = {"patterns": {"manual_pattern": {"category": "manual_category"}}}
    overrides_rules_data = {"patterns": {"override_pattern": {"category": "override_category"}}}

    mock_path_exists.return_value = True
    mock_json_load.side_effect = [overrides_rules_data, manual_rules_data, base_rules_data]

    classification_engine.RULE_SOURCES = [
        ("overrides.json", 0),
        ("manual_rules.json", 1),
        ("base_rules.json", 2),
    ]

    with patch(
        "dewey.core.bookkeeping.classification_engine.Path", return_value=rules_dir
    ):
        prioritized_rules = classification_engine.load_prioritized_rules()

    # Assert that rules are loaded and sorted by priority
    assert len(prioritized_rules) == 3
    assert prioritized_rules[0][0][0] == "override_pattern"
    assert prioritized_rules[1][0][0] == "manual_pattern"
    assert prioritized_rules[2][0][0] == "base_pattern"


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", side_effect=FileNotFoundError)
def test_load_prioritized_rules_file_not_found(mock_open_file, mock_path_exists, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path, caplog) -> None:
    """Test loading prioritized rules when a file is not found."""
    caplog.set_level(logging.WARNING)
    rules_dir = tmp_path / "rules"
    classification_engine.RULE_SOURCES = [("nonexistent_rules.json", 0)]
    mock_path_exists.return_value = False

    with patch(
        "dewey.core.bookkeeping.classification_engine.Path", return_value=rules_dir
    ):
        prioritized_rules = classification_engine.load_prioritized_rules()

    assert len(prioritized_rules) == 0
    assert "Rules file not found" in caplog.text


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
@patch("json.load", side_effect=json.JSONDecodeError("", "", 0))
def test_load_prioritized_rules_invalid_json(mock_json_load, mock_open_file, mock_path_exists, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path, caplog) -> None:
    """Test loading prioritized rules from an invalid JSON file."""
    caplog.set_level(logging.ERROR)
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    invalid_rules_path = rules_dir / "invalid_rules.json"
    classification_engine.RULE_SOURCES = [("invalid_rules.json", 0)]
    mock_path_exists.return_value = True

    with patch(
        "dewey.core.bookkeeping.classification_engine.Path", return_value=rules_dir
    ):
        prioritized_rules = classification_engine.load_prioritized_rules()

    assert len(prioritized_rules) == 0
    assert "Error decoding JSON" in caplog.text


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_format_category(mock_base_script, classification_engine: ClassificationEngine) -> None:
    """Test formatting a category string."""
    assert classification_engine.format_category(" test_category ") == "expenses:test_category"
    assert classification_engine.format_category("income:test_category") == "income:test_category"


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_compile_pattern(mock_base_script, classification_engine: ClassificationEngine) -> None:
    """Test compiling a regex pattern."""
    pattern = "test_pattern"
    compiled_pattern = classification_engine.compile_pattern(pattern)
    assert isinstance(compiled_pattern, re.Pattern)


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
def test_compile_pattern_invalid_regex(mock_base_script, classification_engine: ClassificationEngine, caplog, classification_engine: ClassificationEngine) -> None:
    """Test compiling an invalid regex pattern."""
    caplog.set_level(logging.ERROR)
    pattern = "["
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine.compile_pattern(pattern)
    assert "Invalid regex pattern" in str(exc_info.value)
    assert "Invalid regex pattern" in caplog.text


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open)
def test_export_hledger_rules(mock_open_file, mock_path_exists, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path, rules_data: Dict[str, Any]) -> None:
    """Test exporting rules in hledger's CSV format."""
    mock_path_exists.return_value = True
    classification_engine.rules = rules_data
    output_path = tmp_path / "hledger_rules.csv"
    classification_engine.export_hledger_rules(output_path)
    mock_open_file.assert_called_with(output_path, "w")
    handle = mock_open_file()
    content = handle.write.call_args[0][0]
    assert "skip 1" in content
    assert "account2 expenses:unknown" in content
    assert "account2 income:unknown" in content
    assert "if pattern1" in content
    assert "account2 category1" in content


@patch("dewey.core.bookkeeping.classification_engine.BaseScript.__init__", return_value=None)
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open)
def test_export_paisa_template(mock_open_file, mock_path_exists, mock_base_script, classification_engine: ClassificationEngine, tmp_path: Path, rules_data: Dict[str, Any]) -> None:
    """Test exporting rules in Paisa's template format."""
    mock_path_exists.return_value = True
    classification_engine.rules = rules_data
    output_path = tmp_path / "paisa_template.txt"
    classification_engine.export_paisa_template(output_path)
    mock_open_file.assert_called_with(output_path, "w")
    handle = mock_open_file()
    content = handle.write.call_args[0][0]
    assert "{{#if (isDate ROW.A date_format)}}" in content
    assert 'category1="pattern1"' in content
    assert "Assets:Mercury:Checking  {{negate (amount ROW.C)}}" in content

