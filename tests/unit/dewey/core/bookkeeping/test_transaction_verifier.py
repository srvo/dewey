"""Tests for dewey.core.bookkeeping.transaction_verifier."""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from dewey.core.bookkeeping.classification_engine import (
    ClassificationEngine,
    ClassificationError,
)
from dewey.core.bookkeeping.transaction_verifier import ClassificationVerifier, LLMClientInterface
from dewey.core.bookkeeping.writers.journal_writer_fab1858b import JournalWriter
from dewey.core.base_script import BaseScript


@pytest.fixture
def mock_config(tmp_path: Path) -> Dict[str, Any]:
    """Fixture to create a mock configuration file."""
    rules_path = tmp_path / "rules.json"
    rules_path.write_text('{"rules": []}')
    journal_path = tmp_path / "journal.ledger"
    journal_path.write_text("")

    config = {
        "bookkeeping": {
            "rules_path": str(rules_path),
            "journal_path": str(journal_path),
        },
        "llm": {},
        "core": {"logging": {}},
    }

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return config


@pytest.fixture
def mock_classification_engine() -> MagicMock:
    """Fixture to create a mock ClassificationEngine instance."""
    return MagicMock(spec=ClassificationEngine)


@pytest.fixture
def mock_journal_writer() -> MagicMock:
    """Fixture to create a mock JournalWriter instance."""
    return MagicMock(spec=JournalWriter)


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Fixture to create a mock LLMClientInterface instance."""
    return MagicMock(spec=LLMClientInterface)


@pytest.fixture
def classification_verifier(
    mock_config: Dict[str, Any],
    mock_classification_engine: MagicMock,
    mock_journal_writer: MagicMock,
    mock_llm_client: MagicMock,
    tmp_path: Path,
) -> ClassificationVerifier:
    """Fixture to create a ClassificationVerifier instance with mocked config and dependencies."""
    with patch("dewey.core.base_script.CONFIG_PATH", str(tmp_path / "config.yaml")):
        verifier = ClassificationVerifier(
            classification_engine=mock_classification_engine,
            journal_writer=mock_journal_writer,
            llm_client=mock_llm_client,
        )
        verifier.config = mock_config
        verifier.logger = MagicMock()
        return verifier


@pytest.fixture
def mock_transaction() -> Dict[str, Any]:
    """Fixture to create a mock transaction dictionary."""
    return {
        "date": "2024-01-01",
        "description": "Test Transaction",
        "amount": "$10.00",
        "account": "Expenses:Unknown",
    }


def test_classification_verifier_initialization(
    classification_verifier: ClassificationVerifier,
    mock_classification_engine: MagicMock,
    mock_journal_writer: MagicMock,
) -> None:
    """Test that ClassificationVerifier initializes correctly."""
    assert isinstance(classification_verifier, ClassificationVerifier)
    assert classification_verifier.engine == mock_classification_engine
    assert isinstance(classification_verifier.writer, MagicMock)  # Check if it's a MagicMock
    assert classification_verifier.processed_feedback == 0
    assert classification_verifier.rules_path.exists()
    assert classification_verifier.journal_path.exists()


def test_valid_categories(
    classification_verifier: ClassificationVerifier, mock_classification_engine: MagicMock
) -> None:
    """Test that valid_categories property returns the correct categories."""
    mock_classification_engine.categories = ["Category1", "Category2"]
    assert classification_verifier.valid_categories == ["Category1", "Category2"]


def test_get_ai_suggestion_success(
    classification_verifier: ClassificationVerifier, mock_llm_client: MagicMock
) -> None:
    """Test that get_ai_suggestion returns a suggestion on success."""
    mock_llm_client.classify_text.return_value = "Category:Subcategory"
    suggestion = classification_verifier.get_ai_suggestion("Test Description")
    assert suggestion == "Category:Subcategory"
    mock_llm_client.classify_text.assert_called_once()


def test_get_ai_suggestion_empty_response(
    classification_verifier: ClassificationVerifier, mock_llm_client: MagicMock
) -> None:
    """Test that get_ai_suggestion returns an empty string when the AI returns nothing."""
    mock_llm_client.classify_text.return_value = None
    suggestion = classification_verifier.get_ai_suggestion("Test Description")
    assert suggestion == ""
    mock_llm_client.classify_text.assert_called_once()


def test_get_ai_suggestion_failure(
    classification_verifier: ClassificationVerifier, mock_llm_client: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that get_ai_suggestion handles exceptions and logs them."""
    mock_llm_client.classify_text.side_effect = Exception("AI Error")
    with caplog.at_level(logging.ERROR):
        suggestion = classification_verifier.get_ai_suggestion("Test Description")
    assert suggestion == ""
    assert "AI classification failed" in caplog.text
    assert "AI Error" in caplog.text


@patch("subprocess.run")
def test_get_transaction_samples_success(
    mock_subprocess_run: MagicMock, classification_verifier: ClassificationVerifier
) -> None:
    """Test that get_transaction_samples returns a list of transactions on success."""
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = (
        "date,description,amount,account\n"
        "2024-01-01,Test Transaction,$10.00,Expenses:Unknown\n"
        "2024-01-02,Another Transaction,$-20.00,Income:Salary"
    )

    samples = classification_verifier.get_transaction_samples(limit=10)
    assert isinstance(samples, list)
    assert len(samples) == 2
    assert samples[0]["description"] == "Test Transaction"
    assert samples[1]["amount"] == "$-20.00"


@patch("subprocess.run")
def test_get_transaction_samples_hledger_failure(
    mock_subprocess_run: MagicMock, classification_verifier: ClassificationVerifier, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that get_transaction_samples handles hledger failure and logs the error."""
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stderr = "Hledger Error"

    with caplog.at_level(logging.ERROR):
        samples = classification_verifier.get_transaction_samples(limit=10)

    assert samples == []
    assert "hledger export failed" in caplog.text
    assert "Hledger Error" in caplog.text


@patch("subprocess.run")
def test_get_transaction_samples_duckdb_failure(
    mock_subprocess_run: MagicMock, classification_verifier: ClassificationVerifier, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that get_transaction_samples handles DuckDB processing failure and logs the error."""
    mock_subprocess_run.side_effect = Exception("DuckDB Error")

    with caplog.at_level(logging.ERROR):
        samples = classification_verifier.get_transaction_samples(limit=10)

    assert samples == []
    assert "DuckDB processing failed" in caplog.text
    assert "DuckDB Error" in caplog.text


def test_prompt_for_feedback_invalid_transaction_format(
    classification_verifier: ClassificationVerifier, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that prompt_for_feedback handles invalid transaction format."""
    with caplog.at_level(logging.ERROR):
        classification_verifier.prompt_for_feedback("not a dict")  # type: ignore

    assert "Invalid transaction format" in caplog.text
    assert "expected dict, got" in caplog.text


@patch("dewey.core.bookkeeping.transaction_verifier.confirm")
@patch("dewey.core.bookkeeping.transaction_verifier.prompt")
def test_prompt_for_feedback_correct_classification(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    classification_verifier: ClassificationVerifier,
    mock_transaction: Dict[str, Any],
    mock_llm_client: MagicMock,
) -> None:
    """Test that prompt_for_feedback handles correct classification."""
    mock_confirm.return_value = True
    classification_verifier.prompt_for_feedback(mock_transaction)
    mock_prompt.assert_not_called()


@patch("dewey.core.bookkeeping.transaction_verifier.confirm")
@patch("dewey.core.bookkeeping.transaction_verifier.prompt")
def test_prompt_for_feedback_incorrect_classification(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    classification_verifier: ClassificationVerifier,
    mock_transaction: Dict[str, Any],
    mock_classification_engine: MagicMock,
) -> None:
    """Test that prompt_for_feedback handles incorrect classification and updates the classification."""
    mock_confirm.return_value = False
    mock_prompt.return_value = "New:Category"
    mock_classification_engine.process_feedback.return_value = None
    classification_verifier.get_ai_suggestion = MagicMock(return_value="Suggested:Category")  # type: ignore

    classification_verifier.prompt_for_feedback(mock_transaction)

    mock_prompt.assert_called_once()
    mock_classification_engine.process_feedback.assert_called_once()
    assert classification_verifier.processed_feedback == 1


@patch("dewey.core.bookkeeping.transaction_verifier.confirm")
@patch("dewey.core.bookkeeping.transaction_verifier.prompt")
def test_prompt_for_feedback_invalid_category(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    classification_verifier: ClassificationVerifier,
    mock_transaction: Dict[str, Any],
    mock_classification_engine: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that prompt_for_feedback handles invalid category and logs the error."""
    mock_confirm.return_value = False
    mock_prompt.return_value = "Invalid Category"
    mock_classification_engine.process_feedback.side_effect = ClassificationError("Invalid")
    classification_verifier.get_ai_suggestion = MagicMock(return_value="Suggested:Category")  # type: ignore

    with caplog.at_level(logging.ERROR):
        classification_verifier.prompt_for_feedback(mock_transaction)

    assert "Invalid category" in caplog.text
    assert "Invalid" in caplog.text


@patch("dewey.core.bookkeeping.transaction_verifier.confirm")
@patch("dewey.core.bookkeeping.transaction_verifier.prompt")
def test_prompt_for_feedback_processing_error(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    classification_verifier: ClassificationVerifier,
    mock_transaction: Dict[str, Any],
    mock_llm_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that prompt_for_feedback handles errors during transaction processing."""
    mock_confirm.side_effect = Exception("Processing Error")
    mock_llm_client.classify_text.return_value = "Suggested:Category"

    with caplog.at_level(logging.ERROR):
        classification_verifier.prompt_for_feedback(mock_transaction)

    assert "Error processing transaction" in caplog.text
    assert "Processing Error" in caplog.text
    assert "Problematic transaction data" in caplog.text


def test_generate_report(classification_verifier: ClassificationVerifier, caplog: pytest.LogCaptureFixture) -> None:
    """Test that generate_report generates a report when feedback is processed."""
    classification_verifier.processed_feedback = 5
    with caplog.at_level(logging.INFO):
        classification_verifier.generate_report(10)
    # Currently generate_report does nothing, so no log messages are expected.
    assert "" == caplog.text


@patch.object(ClassificationVerifier, "get_transaction_samples")
@patch.object(ClassificationVerifier, "prompt_for_feedback")
def test_run_success(
    mock_prompt_for_feedback: MagicMock,
    mock_get_transaction_samples: MagicMock,
    classification_verifier: ClassificationVerifier,
) -> None:
    """Test that run executes the verification workflow successfully."""
    mock_get_transaction_samples.return_value = [{"description": "Transaction 1"}, {"description": "Transaction 2"}]
    classification_verifier.run()
    assert mock_prompt_for_feedback.call_count == 2


@patch.object(ClassificationVerifier, "get_transaction_samples")
def test_run_no_samples(
    mock_get_transaction_samples: MagicMock,
    classification_verifier: ClassificationVerifier,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that run handles the case where no transactions are found."""
    mock_get_transaction_samples.return_value = []
    with caplog.at_level(logging.ERROR):
        classification_verifier.run()
    assert "No transactions found for verification" in caplog.text


def test_get_path_absolute_path(classification_verifier: ClassificationVerifier) -> None:
    """Test that get_path returns the same path if it's absolute."""
    absolute_path = "/absolute/path"
    result = classification_verifier.get_path(absolute_path)
    assert str(result) == absolute_path


@patch("os.path.isabs")
def test_get_path_relative_path(classification_verifier: ClassificationVerifier, mock_isabs: MagicMock) -> None:
    """Test that get_path returns the correct absolute path for relative paths."""
    mock_isabs.return_value = False
    relative_path = "relative/path"
    expected_path = classification_verifier.PROJECT_ROOT / relative_path
    result = classification_verifier.get_path(relative_path)
    assert result == expected_path


def test_get_config_value_existing_key(classification_verifier: ClassificationVerifier) -> None:
    """Test that get_config_value returns the correct value for existing keys."""
    classification_verifier.config = {"section": {"key": "value"}}
    result = classification_verifier.get_config_value("section.key")
    assert result == "value"


def test_get_config_value_missing_key(classification_verifier: ClassificationVerifier) -> None:
    """Test that get_config_value returns the default value for missing keys."""
    classification_verifier.config = {"section": {}}
    result = classification_verifier.get_config_value("section.missing_key", "default")
    assert result == "default"


def test_get_config_value_nested_missing_key(classification_verifier: ClassificationVerifier) -> None:
    """Test that get_config_value returns the default value for nested missing keys."""
    classification_verifier.config = {}
    result = classification_verifier.get_config_value("missing_section.missing_key", "default")
    assert result == "default"


def test_get_config_value_no_default(classification_verifier: ClassificationVerifier) -> None:
    """Test that get_config_value returns None when the key is missing and no default is provided."""
    classification_verifier.config = {}
    result = classification_verifier.get_config_value("missing_section.missing_key")
    assert result is None


def test_process_hledger_csv_success(classification_verifier: ClassificationVerifier) -> None:
    """Test that _process_hledger_csv processes CSV data correctly."""
    csv_data = (
        "date,description,amount,account\n"
        "2024-01-01,Test Transaction,$10.00,Expenses:Unknown\n"
        "2024-01-02,Another Transaction,$-20.00,Income:Salary"
    )
    transactions = classification_verifier._process_hledger_csv(csv_data)
    assert len(transactions) == 2
    assert transactions[0]["description"] == "Test Transaction"
    assert transactions[1]["amount"] == "$-20.00"


def test_process_hledger_csv_duckdb_failure(
    classification_verifier: ClassificationVerifier, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that _process_hledger_csv handles DuckDB processing failure and logs the error."""
    csv_data = "invalid csv data"
    with patch("duckdb.connect", side_effect=Exception("DuckDB Error")):
        with caplog.at_level(logging.ERROR):
            transactions = classification_verifier._process_hledger_csv(csv_data)
    assert transactions == []
    assert "DuckDB processing failed" in caplog.text
    assert "DuckDB Error" in caplog.text
