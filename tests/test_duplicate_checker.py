import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from _pytest.capture import caplog
from duplicate_checker import (
    find_ledger_files,
    check_duplicates,
    main,
    DuplicateCheckerError,
)

def test_find_ledger_files_no_files(tmp_path: Path) -> None:
    """Test find_ledger_files returns empty dict when no .journal files exist."""
    # Arrange
    test_dir = tmp_path
    
    # Act
    result = find_ledger_files(test_dir)
    
    # Assert
    assert result == {}
    assert isinstance(result, dict)

def test_find_ledger_files_single_file(tmp_path: Path) -> None:
    """Test single .journal file is found and hashed correctly."""
    # Arrange
    test_file = tmp_path / "test.journal"
    test_file.touch()
    
    # Act
    result = find_ledger_files(tmp_path)
    
    # Assert
    assert len(result) == 1
    assert list(result.values())[0] == [test_file]

def test_find_ledger_files_duplicates(tmp_path: Path) -> None:
    """Test duplicate files are grouped by hash."""
    # Arrange
    content = b"test content"
    (tmp_path / "file1.journal").write_bytes(content)
    (tmp_path / "file2.journal").write_bytes(content)
    
    # Act
    result = find_ledger_files(tmp_path)
    
    # Assert
    assert len(result) == 1
    assert len(result[list(result.keys())[0]]) == 2

def test_find_ledger_files_non_journal_files(tmp_path: Path) -> None:
    """Test non-.journal files are ignored."""
    # Arrange
    (tmp_path / "file.txt").touch()
    
    # Act
    result = find_ledger_files(tmp_path)
    
    # Assert
    assert result == {}

@patch("pathlib.Path.read_bytes")
def test_find_ledger_files_error_handling(mock_read: MagicMock, tmp_path: Path) -> None:
    """Test error handling when file can't be read."""
    mock_read.side_effect = OSError("Permission denied")
    (tmp_path / "broken.journal").touch()
    
    # Act
    result = find_ledger_files(tmp_path)
    
    # Assert
    assert result == {}
    mock_read.assert_called()

def test_check_duplicates_no_duplicates(tmp_path: Path) -> None:
    """Test no duplicates detected."""
    # Arrange
    (tmp_path / "file1.journal").touch()
    (tmp_path / "file2.journal").write_bytes(b"unique content")
    
    # Act
    result = check_duplicates(tmp_path)
    
    # Assert
    assert not result

def test_check_duplicates_with_duplicates(tmp_path: Path) -> None:
    """Test duplicates detected correctly."""
    # Arrange
    content = b"data"
    (tmp_path / "a.journal").write_bytes(content)
    (tmp_path / "b.journal").write_bytes(content)
    
    # Act
    result = check_duplicates(tmp_path)
    
    # Assert
    assert result

@patch("duplicate_checker.find_ledger_files")
def test_check_duplicates_find_error(mock_find: MagicMock) -> None:
    """Test error propagation from find_ledger_files."""
    mock_find.side_effect = DuplicateCheckerError("Test error")
    
    with pytest.raises(DuplicateCheckerError):
        check_duplicates()

def test_main_no_duplicates(tmp_path: Path, mocker) -> None:
    """Test main exits 0 when no duplicates found."""
    mocker.patch("sys.argv", ["script", f"--dir={tmp_path}"])
    mocker.patch("duplicate_checker.check_duplicates", return_value=False)
    mocker.patch("sys.exit")
    
    main()
    assert sys.exit.call_args_list[0][0][0] == 0

def test_main_has_duplicates(tmp_path: Path, mocker) -> None:
    """Test main exits 1 when duplicates found."""
    mocker.patch("sys.argv", ["script", f"--dir={tmp_path}"])
    mocker.patch("duplicate_checker.check_duplicates", return_value=True)
    mocker.patch("sys.exit")
    
    main()
    assert sys.exit.call_args_list[0][0][0] == 1

@patch("duplicate_checker.check_duplicates")
def test_main_duplicate_error(mock_check: MagicMock, mocker) -> None:
    """Test main handles DuplicateCheckerError."""
    mock_check.side_effect = DuplicateCheckerError("Test error")
    mocker.patch("sys.exit")
    
    main()
    assert sys.exit.call_args_list[0][0][0] == 1

def test_main_invalid_directory(tmp_path: Path, mocker) -> None:
    """Test main handles invalid directory paths."""
    invalid_dir = tmp_path / "nonexistent"
    mocker.patch("sys.argv", ["script", f"--dir={invalid_dir}"])
    mocker.patch("sys.exit")
    
    main()
    assert sys.exit.call_args_list[0][0][0] == 1
# Add type hints and docstrings to all test functions
# Ensure all test names follow test_<function>_<scenario> pattern
