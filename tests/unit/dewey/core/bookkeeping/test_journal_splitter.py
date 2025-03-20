import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import mock_open, patch

import pytest

from dewey.core.bookkeeping.journal_splitter import JournalSplitter


@pytest.fixture
def journal_splitter() -> JournalSplitter:
    """Fixture to create a JournalSplitter instance."""
    return JournalSplitter()


@pytest.fixture
def mock_config(tmp_path: Path) -> Dict[str, str]:
    """Fixture to create a mock configuration."""
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    return {"bookkeeping.journal_dir": str(journal_dir)}


@pytest.fixture
def mock_journal_file(tmp_path: Path) -> Path:
    """Fixture to create a mock journal file."""
    journal_content = """2023-01-01 Description 1
    expenses:unknown  100
    income:unknown  -100

2023-02-01 Description 2
    expenses:unknown  200
    income:unknown  -200

2024-01-01 Description 3
    expenses:unknown  300
    income:unknown  -300
"""
    journal_file = tmp_path / "test_1234.journal"
    with open(journal_file, "w") as f:
        f.write(journal_content)
    return journal_file


def test_journal_splitter_initialization(journal_splitter: JournalSplitter) -> None:
    """Test JournalSplitter initialization."""
    assert journal_splitter.config_section == "bookkeeping"
    assert journal_splitter.logger is not None


def test_split_journal_by_year(
    journal_splitter: JournalSplitter, tmp_path: Path, mock_journal_file: Path
) -> None:
    """Test splitting a journal file by year."""
    output_dir = str(tmp_path / "output")
    journal_splitter.split_journal_by_year(str(mock_journal_file), output_dir)

    # Check if the output directory was created
    assert Path(output_dir).exists()

    # Check if the files for each year were created
    file_2023 = Path(output_dir) / "test_1234_2023.journal"
    file_2024 = Path(output_dir) / "test_1234_2024.journal"
    assert file_2023.exists()
    assert file_2024.exists()

    # Check the content of the files
    with open(file_2023, "r") as f:
        content_2023 = f.read()
        assert "2023-01-01 Description 1" in content_2023
        assert "2023-02-01 Description 2" in content_2023
        assert "2024-01-01 Description 3" not in content_2023

    with open(file_2024, "r") as f:
        content_2024 = f.read()
        assert "2024-01-01 Description 3" in content_2024
        assert "2023-01-01 Description 1" not in content_2024


def test_split_journal_by_year_empty_file(
    journal_splitter: JournalSplitter, tmp_path: Path
) -> None:
    """Test splitting an empty journal file."""
    output_dir = str(tmp_path / "output")
    empty_file = tmp_path / "empty.journal"
    empty_file.write_text("")

    journal_splitter.split_journal_by_year(str(empty_file), output_dir)

    # Check if the output directory was created
    assert Path(output_dir).exists()

    # Check if no files were created
    assert len(list(Path(output_dir).iterdir())) == 0


def test_split_journal_by_year_invalid_date(
    journal_splitter: JournalSplitter, tmp_path: Path
) -> None:
    """Test splitting a journal file with an invalid date format."""
    output_dir = str(tmp_path / "output")
    invalid_date_content = "invalid-date-format Description\n  expenses:unknown 100\n  income:unknown -100"
    invalid_date_file = tmp_path / "invalid_date.journal"
    invalid_date_file.write_text(invalid_date_content)

    journal_splitter.split_journal_by_year(str(invalid_date_file), output_dir)

    # Check if the output directory was created
    assert Path(output_dir).exists()

    # Check if no files were created
    assert len(list(Path(output_dir).iterdir())) == 0


def test_split_journal_by_year_replace_accounts(
    journal_splitter: JournalSplitter, tmp_path: Path
) -> None:
    """Test that the account replacement works correctly."""
    output_dir = str(tmp_path / "output")
    account_num = "5678"
    journal_content = f"""2023-01-01 Description 1
    expenses:unknown  100
    income:unknown  -100
"""
    journal_file = tmp_path / f"test_{account_num}.journal"
    with open(journal_file, "w") as f:
        f.write(journal_content)

    journal_splitter.split_journal_by_year(str(journal_file), output_dir)

    output_file = Path(output_dir) / f"test_{account_num}_2023.journal"
    assert output_file.exists()

    with open(output_file, "r") as f:
        content = f.read()
        assert "expenses:unclassified" in content
        assert f"assets:checking:mercury{account_num}" in content


def test_run(journal_splitter: JournalSplitter, tmp_path: Path) -> None:
    """Test the run method."""
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    output_dir = journal_dir / "by_year"
    journal_file1 = journal_dir / "test_1234.journal"
    journal_file1.write_text("2023-01-01 Description\n  expenses:unknown 100\n  income:unknown -100")
    journal_file2 = journal_dir / "test_5678.journal"
    journal_file2.write_text("2024-01-01 Description\n  expenses:unknown 200\n  income:unknown -200")

    with patch.object(journal_splitter, "get_config_value", return_value=str(journal_dir)):
        journal_splitter.run()

    assert output_dir.exists()
    assert (output_dir / "test_1234_2023.journal").exists()
    assert (output_dir / "test_5678_2024.journal").exists()


def test_run_no_journal_files(journal_splitter: JournalSplitter, tmp_path: Path) -> None:
    """Test the run method when there are no journal files."""
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    output_dir = journal_dir / "by_year"

    with patch.object(journal_splitter, "get_config_value", return_value=str(journal_dir)):
        journal_splitter.run()

    assert output_dir.exists()
    assert len(list(output_dir.iterdir())) == 0


def test_run_with_dot_file(journal_splitter: JournalSplitter, tmp_path: Path) -> None:
    """Test the run method when there is a dot file in the journal directory."""
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    output_dir = journal_dir / "by_year"
    dot_file = journal_dir / ".DS_Store"
    dot_file.write_text("")

    with patch.object(journal_splitter, "get_config_value", return_value=str(journal_dir)):
        journal_splitter.run()

    assert output_dir.exists()
    assert len(list(output_dir.iterdir())) == 0


def test_main(journal_splitter: JournalSplitter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the main function."""
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    journal_file = journal_dir / "test_1234.journal"
    journal_file.write_text("2023-01-01 Description\n  expenses:unknown 100\n  income:unknown -100")

    with patch.object(journal_splitter, "get_config_value", return_value=str(journal_dir)):
        with patch.object(JournalSplitter, "execute") as mock_execute:
            monkeypatch.setattr("dewey.core.bookkeeping.journal_splitter.JournalSplitter", lambda: journal_splitter)
            from dewey.core.bookkeeping.journal_splitter import main
            main()
            mock_execute.assert_called_once()
