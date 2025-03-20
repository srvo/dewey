import json
import logging
import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.bookkeeping.classification_engine import (
    ClassificationEngine,
    ClassificationError,
)
from dewey.core.base_script import BaseScript

# Mock BaseScript for testing purposes
class MockBaseScript(BaseScript):
    """Class MockBaseScript."""
    def __init__(self, config_section: str = 'bookkeeping'):
        """Function __init__."""
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Function run."""
        pass

@pytest.fixture
def rules_data() -> Dict[str, Any]:
    """Fixture providing sample rules data."""
    return {
        "patterns": {"pattern1": "category1", "pattern2": "category2"}, "categories": ["category1", "category2", "expenses:unknown", "income:unknown"], "defaults": {"positive": "income:unknown", "negative": "expenses:unknown"}, "overrides": {"override_pattern": {"category": "override_category"}}, "sources": [], "hledger": {"currency": "USD", "date_format": "%Y-%m-%d"}, }


@pytest.fixture
def classification_engine(
    tmp_path: Path, rules_data: Dict[str, Any]
) -> ClassificationEngine:
    """Fixture providing a ClassificationEngine instance."""
    rules_path = tmp_path / "rules.json"
    with open(rules_path, "w") as f:
        json.dump(rules_data, f)
    ledger_file = tmp_path / "ledger.txt"
    return ClassificationEngine(rules_path=rules_path, ledger_file=ledger_file)


@pytest.fixture
def mock_journal_writer() -> MagicMock:
    """Fixture providing a mock JournalWriter instance."""
    return MagicMock()


def test_classification_engine_initialization(
    classification_engine: ClassificationEngine, tmp_path: Path
) -> None:
    """Test ClassificationEngine initialization."""
    assert classification_engine.ledger_file == tmp_path / "ledger.txt"
    assert classification_engine.rules_path.exists()
    assert isinstance(classification_engine.rules, dict)
    assert isinstance(classification_engine.compiled_patterns, dict)


def test_categories_property(classification_engine: ClassificationEngine) -> None:
    """Test the categories property."""
    assert classification_engine.categories == [
        "category1", "category2", "expenses:unknown", "income:unknown", ]


def test_load_rules(
    classification_engine: ClassificationEngine, rules_data: Dict[str, Any], tmp_path: Path
) -> None:
    """Test loading rules from a JSON file."""
    rules = classification_engine._load_rules()
    assert rules["patterns"] == rules_data["patterns"]
    assert rules["categories"] == rules_data["categories"]
    assert rules["defaults"] == rules_data["defaults"]
    assert rules["overrides"] == rules_data["overrides"]


def test_load_rules_file_not_found(classification_engine: ClassificationEngine, tmp_path: Path, caplog) -> None:
    """Test loading rules when the file is not found."""
    caplog.set_level(logging.ERROR)
    classification_engine.rules_path=None, tmp_path: Path, caplog) -> None:
    """Test loading rules from an invalid JSON file."""
    caplog.set_level(logging.ERROR)
    rules_path = tmp_path / "invalid_rules.json"
    with open(rules_path, "w") as f:
        f.write("invalid json")
    classification_engine.rules_path=None, rules_data: Dict[str, Any]
) -> None:
    """Test compiling regex patterns."""
    compiled_patterns = classification_engine._compile_patterns()
    assert isinstance(compiled_patterns, dict)
    assert all(isinstance(p, re.Pattern) for p in compiled_patterns.values())


def test_compile_patterns_invalid_regex(
    classification_engine: ClassificationEngine, rules_data: Dict[str, Any], caplog
) -> None:
    """Test compiling regex patterns with an invalid regex."""
    caplog.set_level(logging.ERROR)
    classification_engine.rules["patterns"]["invalid_pattern"] = "["
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._compile_patterns()
    assert "Invalid regex pattern" in str(exc_info.value)
    assert "Invalid regex pattern" in caplog.text


def test_classify(
    classification_engine: ClassificationEngine, rules_data: Dict[str, Any]
) -> None:
    """Test classifying a transaction."""
    classification_engine.compiled_patterns = (
        classification_engine._compile_patterns()
    )
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


def test_classify_no_match(classification_engine: ClassificationEngine) -> None:
    """Test classifying a transaction with no matching pattern."""
    classification_engine.compiled_patterns = (
        classification_engine._compile_patterns()
    )
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


def test_process_feedback(
    classification_engine: ClassificationEngine, mock_journal_writer: MagicMock, tmp_path: Path
) -> None:
    """Test processing user feedback."""
    feedback = 'Classify "new transaction" as new_category'
    classification_engine.process_feedback(feedback, mock_journal_writer)
    assert "new_transaction" in classification_engine.rules["overrides"]
    assert classification_engine.rules["overrides"]["new_transaction"]["category"] == "new_category"
    mock_journal_writer.log_classification_decision.assert_called_once()


def test_process_feedback_invalid_category(
    classification_engine: ClassificationEngine, mock_journal_writer: MagicMock
) -> None:
    """Test processing user feedback with an invalid category."""
    feedback = 'Classify "new transaction" as invalid_category'
    with pytest.raises(ValueError) as exc_info:
        classification_engine.process_feedback(feedback, mock_journal_writer)
    assert "is not an allowed category" in str(exc_info.value)


def test_parse_feedback(classification_engine: ClassificationEngine) -> None:
    """Test parsing user feedback."""
    feedback = 'Classify "test transaction" as test_category'
    pattern, category = classification_engine._parse_feedback(feedback)
    assert pattern == "test transaction"
    assert category == "test_category"


def test_parse_feedback_invalid_format(classification_engine: ClassificationEngine) -> None:
    """Test parsing user feedback with an invalid format."""
    feedback = "invalid feedback"
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._parse_feedback(feedback)
    assert "Invalid feedback format" in str(exc_info.value)


@patch("dewey.core.bookkeeping.classification_engine.llm_utils.call_llm")
def test_parse_with_ai(
    mock_call_llm: MagicMock, classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI."""
    mock_call_llm.return_value = [{"example": '{"pattern": "ai pattern", "category": "ai_category"}'}]
    feedback = "complex feedback"
    pattern, category = classification_engine._parse_with_ai(feedback)
    assert pattern == "ai pattern"
    assert category == "ai_category"
    mock_call_llm.assert_called_once()


@patch("dewey.core.bookkeeping.classification_engine.llm_utils.call_llm")
def test_parse_with_ai_no_response(
    mock_call_llm: MagicMock, classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI when there is no response."""
    mock_call_llm.return_value=None, classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI when parsing fails."""
    mock_call_llm.return_value = [{"example": "invalid json"}]
    feedback = "complex feedback"
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._parse_with_ai(feedback)
    assert "AI parsing failed" in str(exc_info.value)
    mock_call_llm.assert_called_once()


def test_save_overrides(
    classification_engine: ClassificationEngine, rules_data: Dict[str, Any], tmp_path: Path
) -> None:
    """Test saving override rules to file."""
    overrides_file = tmp_path.parent / "src" / "dewey" / "core" / "rules" / "overrides.json"
    overrides_file.parent.mkdir(parents=True, exist_ok=True)
    classification_engine.rules["overrides"] = {"pattern1": {"category": "category1"}}
    classification_engine._save_overrides()
    with open(overrides_file, "r") as f:
        data = json.load(f)
    assert "pattern1" in data["patterns"]
    assert "category1" in data["categories"]


def test_validate_category(classification_engine: ClassificationEngine) -> None:
    """Test validating a category."""
    classification_engine._validate_category("category1")  # Valid category
    with pytest.raises(ValueError) as exc_info:
        classification_engine._validate_category("invalid_category")
    assert "is not an allowed category" in str(exc_info.value)


def test_load_prioritized_rules(
    classification_engine: ClassificationEngine, tmp_path: Path
) -> None:
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

    with open(base_rules_path, "w") as f:
        json.dump(base_rules_data, f)
    with open(manual_rules_path, "w") as f:
        json.dump(manual_rules_data, f)
    with open(overrides_rules_path, "w") as f:
        json.dump(overrides_rules_data, f)

    classification_engine.RULE_SOURCES = [
        ("overrides.json", 0), ("manual_rules.json", 1), ("base_rules.json", 2), ]

    with patch(
        "dewey.core.bookkeeping.classification_engine.Path", return_value=rules_dir
    ):
        if caplog) -> None:
    """Test loading rules when the file is not found."""
    caplog.set_level(logging.ERROR)
    classification_engine.rules_path is None:
            caplog) -> None:
    """Test loading rules when the file is not found."""
    caplog.set_level(logging.ERROR)
    classification_engine.rules_path = tmp_path / "nonexistent_rules.json"
    rules = classification_engine._load_rules()
    assert rules["patterns"] == {}
    assert "Failed to load classification rules" in caplog.text


def test_load_rules_invalid_json(classification_engine: ClassificationEngine
        if "w") as f:
        f.write("invalid json")
    classification_engine.rules_path is None:
            "w") as f:
        f.write("invalid json")
    classification_engine.rules_path = rules_path
    rules = classification_engine._load_rules()
    assert rules["patterns"] == {}
    assert "Failed to load classification rules" in caplog.text


def test_compile_patterns(
    classification_engine: ClassificationEngine
        if classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI when there is no response."""
    mock_call_llm.return_value is None:
            classification_engine: ClassificationEngine
) -> None:
    """Test parsing feedback with AI when there is no response."""
    mock_call_llm.return_value = []
    feedback = "complex feedback"
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine._parse_with_ai(feedback)
    assert "No response from AI" in str(exc_info.value)
    mock_call_llm.assert_called_once()


@patch("dewey.core.bookkeeping.classification_engine.llm_utils.call_llm")
def test_parse_with_ai_parsing_fails(
    mock_call_llm: MagicMock
        prioritized_rules = classification_engine.load_prioritized_rules()

    # Assert that rules are loaded and sorted by priority
    assert len(prioritized_rules) == 3
    assert prioritized_rules[0][0][0] == "override_pattern"
    assert prioritized_rules[1][0][0] == "manual_pattern"
    assert prioritized_rules[2][0][0] == "base_pattern"


def test_load_prioritized_rules_file_not_found(
    classification_engine: ClassificationEngine, tmp_path: Path, caplog
) -> None:
    """Test loading prioritized rules when a file is not found."""
    caplog.set_level(logging.WARNING)
    rules_dir = tmp_path / "rules"
    classification_engine.RULE_SOURCES = [("nonexistent_rules.json", 0)]

    with patch(
        "dewey.core.bookkeeping.classification_engine.Path", return_value=rules_dir
    ):
        prioritized_rules = classification_engine.load_prioritized_rules()

    assert len(prioritized_rules) == 0
    assert "Rules file not found" in caplog.text


def test_load_prioritized_rules_invalid_json(
    classification_engine: ClassificationEngine, tmp_path: Path, caplog
) -> None:
    """Test loading prioritized rules from an invalid JSON file."""
    caplog.set_level(logging.ERROR)
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    invalid_rules_path = rules_dir / "invalid_rules.json"
    with open(invalid_rules_path, "w") as f:
        f.write("invalid json")
    classification_engine.RULE_SOURCES = [("invalid_rules.json", 0)]

    with patch(
        "dewey.core.bookkeeping.classification_engine.Path", return_value=rules_dir
    ):
        prioritized_rules = classification_engine.load_prioritized_rules()

    assert len(prioritized_rules) == 0
    assert "Error decoding JSON" in caplog.text


def test_format_category(classification_engine: ClassificationEngine) -> None:
    """Test formatting a category string."""
    assert classification_engine.format_category(" test_category ") == "expenses:test_category"
    assert classification_engine.format_category("income:test_category") == "income:test_category"


def test_compile_pattern(classification_engine: ClassificationEngine) -> None:
    """Test compiling a regex pattern."""
    pattern = "test_pattern"
    compiled_pattern = classification_engine.compile_pattern(pattern)
    assert isinstance(compiled_pattern, re.Pattern)


def test_compile_pattern_invalid_regex(classification_engine: ClassificationEngine, caplog) -> None:
    """Test compiling an invalid regex pattern."""
    caplog.set_level(logging.ERROR)
    pattern = "["
    with pytest.raises(ClassificationError) as exc_info:
        classification_engine.compile_pattern(pattern)
    assert "Invalid regex pattern" in str(exc_info.value)
    assert "Invalid regex pattern" in caplog.text


def test_export_hledger_rules(classification_engine: ClassificationEngine, tmp_path: Path) -> None:
    """Test exporting rules in hledger's CSV format."""
    output_path = tmp_path / "hledger_rules.csv"
    classification_engine.export_hledger_rules(output_path)
    assert output_path.exists()
    with open(output_path, "r") as f:
        content = f.read()
    assert "skip 1" in content
    assert "account2 expenses:unknown" in content
    assert "account2 income:unknown" in content
    assert "if pattern1" in content
    assert "account2 category1" in content


def test_export_paisa_template(classification_engine: ClassificationEngine, tmp_path: Path) -> None:
    """Test exporting rules in Paisa's template format."""
    output_path = tmp_path / "paisa_template.txt"
    classification_engine.export_paisa_template(output_path)
    assert output_path.exists()
    with open(output_path, "r") as f:
        content = f.read()
    assert "{{#if (isDate ROW.A date_format)}}" in content
    assert 'category1="pattern1"' in content
    assert "Assets:Mercury:Checking  {{negate (amount ROW.C)}}" in content
