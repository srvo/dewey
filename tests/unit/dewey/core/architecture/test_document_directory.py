"""Tests for dewey.core.architecture.document_directory."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Any, Dict, List, Optional, Tuple

import pytest
import yaml

from dewey.core.architecture.document_directory import (
    DirectoryDocumenter,
    CONVENTIONS_PATH,
)
from dewey.core.base_script import BaseScript


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Fixture to mock BaseScript."""
    mock = MagicMock(spec=BaseScript)
    mock.logger = MagicMock()
    mock.config = {}
    mock.get_path = MagicMock(return_value=Path("."))
    mock.get_config_value = MagicMock(return_value="test_value")
    mock.llm_client = MagicMock()
    return mock


@pytest.fixture
def documenter(tmp_path: Path, mock_base_script: MagicMock) -> DirectoryDocumenter:
    """Fixture to create a DirectoryDocumenter instance with a temporary directory."""
    conventions_file = tmp_path / "CONVENTIONS.md"
    conventions_file.write_text("Project Conventions")
    global CONVENTIONS_PATH
    CONVENTIONS_PATH = conventions_file
    checkpoint_file = tmp_path / ".dewey_documenter_checkpoint.json"
    root_dir = tmp_path
    documenter = DirectoryDocumenter(root_dir=str(root_dir))
    documenter.logger = mock_base_script.logger
    documenter.config = mock_base_script.config
    documenter.conventions_path = conventions_file
    documenter.checkpoint_file = checkpoint_file
    documenter.llm_client = mock_base_script.llm_client
    return documenter


def test_directory_documenter_init(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test the initialization of the DirectoryDocumenter class."""
    assert documenter.root_dir == tmp_path.resolve()
    assert documenter.conventions_path.exists()
    assert documenter.checkpoints == {}
    assert documenter.conventions == "Project Conventions"


def test_directory_documenter_init_no_conventions(tmp_path: Path, mock_base_script: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test initialization when CONVENTIONS.md is not found."""
    monkeypatch.setattr(sys, 'exit', lambda x: None)
    conventions_path = tmp_path / "missing_conventions.md"
    global CONVENTIONS_PATH
    CONVENTIONS_PATH = conventions_path
    with pytest.raises(SystemExit):
        DirectoryDocumenter(root_dir=str(tmp_path))


def test_validate_directory_exists(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _validate_directory raises an error if the directory doesn't exist."""
    non_existent_dir = tmp_path / "non_existent"
    documenter.root_dir = non_existent_dir
    with pytest.raises(FileNotFoundError):
        documenter._validate_directory()


def test_validate_directory_access(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _validate_directory raises an error if the directory is not accessible."""
    # Create a directory with no read access
    if os.name == 'posix':  # Skip on Windows
        no_access_dir = tmp_path / "no_access"
        no_access_dir.mkdir()
        no_access_dir.chmod(0o000)  # Remove all permissions
        documenter.root_dir = no_access_dir
        with pytest.raises(PermissionError):
            documenter._validate_directory()
        no_access_dir.chmod(0o777)  # Restore permissions
    else:
        pytest.skip("Skipping permission test on non-POSIX system")


def test_load_conventions(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _load_conventions loads the conventions from the CONVENTIONS.md file."""
    conventions_file = tmp_path / "CONVENTIONS.md"
    conventions_file.write_text("Test Conventions")
    documenter.conventions_path = conventions_file
    conventions = documenter._load_conventions()
    assert conventions == "Test Conventions"


def test_load_conventions_not_found(documenter: DirectoryDocumenter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that _load_conventions handles the case where the CONVENTIONS.md file is not found."""
    monkeypatch.setattr(sys, 'exit', lambda x: None)
    documenter.conventions_path = tmp_path / "missing_conventions.md"
    with pytest.raises(SystemExit):
        documenter._load_conventions()


def test_load_conventions_error(documenter: DirectoryDocumenter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that _load_conventions handles errors when loading the conventions file."""
    monkeypatch.setattr(sys, 'exit', lambda x: None)
    documenter.conventions_path = tmp_path / "CONVENTIONS.md"
    documenter.conventions_path.write_text("Test Conventions")
    with patch("dewey.core.architecture.document_directory.open", side_effect=Exception("Failed to open")):
        with pytest.raises(SystemExit):
            documenter._load_conventions()


def test_load_checkpoints(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _load_checkpoints loads checkpoint data from a file."""
    checkpoint_data = {"file1.py": "hash1", "file2.py": "hash2"}
    checkpoint_file = tmp_path / ".dewey_documenter_checkpoint.json"
    checkpoint_file.write_text(json.dumps(checkpoint_data))
    documenter.checkpoint_file = checkpoint_file
    checkpoints = documenter._load_checkpoints()
    assert checkpoints == checkpoint_data


def test_load_checkpoints_no_file(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _load_checkpoints returns an empty dictionary if the checkpoint file doesn't exist."""
    documenter.checkpoint_file = tmp_path / "non_existent_checkpoint.json"
    checkpoints = documenter._load_checkpoints()
    assert checkpoints == {}


def test_load_checkpoints_invalid_json(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _load_checkpoints handles invalid JSON in the checkpoint file."""
    checkpoint_file = tmp_path / ".dewey_documenter_checkpoint.json"
    checkpoint_file.write_text("invalid json")
    documenter.checkpoint_file = checkpoint_file
    documenter.logger.warning = MagicMock()
    checkpoints = documenter._load_checkpoints()
    assert checkpoints == {}
    documenter.logger.warning.assert_called_once()


def test_save_checkpoints(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _save_checkpoints saves checkpoint data to a file."""
    checkpoint_data = {"file1.py": "hash1", "file2.py": "hash2"}
    documenter.checkpoints = checkpoint_data
    documenter.checkpoint_file = tmp_path / ".dewey_documenter_checkpoint.json"
    documenter._save_checkpoints()
    with open(documenter.checkpoint_file) as f:
        saved_data = json.load(f)
    assert saved_data == checkpoint_data


def test_save_checkpoints_error(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _save_checkpoints handles errors when saving the checkpoint file."""
    documenter.checkpoints = {"file1.py": "hash1"}
    documenter.checkpoint_file = tmp_path / ".dewey_documenter_checkpoint.json"
    documenter.logger.exception = MagicMock()
    with patch("dewey.core.architecture.document_directory.open", side_effect=Exception("Failed to open")):
        documenter._save_checkpoints()
    documenter.logger.exception.assert_called_once()


def test_calculate_file_hash(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _calculate_file_hash calculates the SHA256 hash of a file's contents."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")
    file_hash = documenter._calculate_file_hash(file_path)
    assert isinstance(file_hash, str)
    assert file_hash == f"{len('Test content')}_" + hashlib.sha256("Test content".encode()).hexdigest()


def test_calculate_file_hash_empty_file(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _calculate_file_hash returns 'empty_file' for an empty file."""
    file_path = tmp_path / "empty_file.txt"
    file_path.write_text("")
    file_hash = documenter._calculate_file_hash(file_path)
    assert file_hash == "empty_file"


def test_calculate_file_hash_error(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _calculate_file_hash handles errors when calculating the hash."""
    file_path = tmp_path / "test_file.txt"
    documenter.logger.exception = MagicMock()
    with patch("dewey.core.architecture.document_directory.open", side_effect=Exception("Failed to open")):
        with pytest.raises(Exception):
            documenter._calculate_file_hash(file_path)
    documenter.logger.exception.assert_called_once()


def test_is_checkpointed(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _is_checkpointed checks if a file has been processed based on its content hash."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")
    file_hash = f"{len('Test content')}_" + hashlib.sha256("Test content".encode()).hexdigest()
    documenter.checkpoints = {str(file_path): file_hash}
    assert documenter._is_checkpointed(file_path)


def test_is_checkpointed_not_found(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _is_checkpointed returns False if the file is not in the checkpoints."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")
    documenter.checkpoints = {}
    assert not documenter._is_checkpointed(file_path)


def test_is_checkpointed_hash_mismatch(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _is_checkpointed returns False if the file's hash doesn't match the checkpointed hash."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")
    documenter.checkpoints = {str(file_path): "wrong_hash"}
    assert not documenter._is_checkpointed(file_path)


def test_is_checkpointed_error(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _is_checkpointed handles errors when reading the file to check the checkpoint."""
    file_path = tmp_path / "test_file.txt"
    documenter.logger.exception = MagicMock()
    with patch("dewey.core.architecture.document_directory.DirectoryDocumenter._calculate_file_hash", side_effect=Exception("Failed to read")):
        assert not documenter._is_checkpointed(file_path)
    documenter.logger.exception.assert_called_once()


def test_checkpoint(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _checkpoint checkpoints a file by saving its content hash."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")
    documenter._checkpoint(file_path)
    file_hash = f"{len('Test content')}_" + hashlib.sha256("Test content".encode()).hexdigest()
    assert documenter.checkpoints[str(file_path)] == file_hash


def test_checkpoint_error(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _checkpoint handles errors when checkpointing a file."""
    file_path = tmp_path / "test_file.txt"
    documenter.logger.exception = MagicMock()
    with patch("dewey.core.architecture.document_directory.open", side_effect=Exception("Failed to open")):
        documenter._checkpoint(file_path)
    documenter.logger.exception.assert_called_once()


@patch("dewey.core.architecture.document_directory.generate_content")
def test_analyze_code(mock_generate_content: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that analyze_code analyzes the given code using an LLM and returns a summary."""
    mock_generate_content.return_value = "Analysis\n4. core.module"
    code = "Test code"
    analysis, suggested_module = documenter.analyze_code(code)
    assert analysis == "Analysis"
    assert suggested_module == "core.module"
    mock_generate_content.assert_called_once()


@patch("dewey.core.architecture.document_directory.generate_content", side_effect=Exception("LLM failed"))
def test_analyze_code_error(mock_generate_content: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that analyze_code handles errors during code analysis."""
    code = "Test code"
    documenter.logger.exception = MagicMock()
    with pytest.raises(Exception):
        documenter.analyze_code(code)
    documenter.logger.exception.assert_called_once()


@patch("subprocess.run")
def test_analyze_code_quality(mock_subprocess_run: MagicMock, documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _analyze_code_quality runs code quality checks using flake8 and ruff."""
    mock_subprocess_run.return_value.stdout = "flake8 output\nruff output"
    file_path = tmp_path / "test_file.py"
    file_path.write_text("Test code")
    results = documenter._analyze_code_quality(file_path)
    assert "flake8" in results
    assert "ruff" in results
    mock_subprocess_run.assert_called()


@patch("subprocess.run", side_effect=Exception("Subprocess failed"))
def test_analyze_code_quality_error(mock_subprocess_run: MagicMock, documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _analyze_code_quality handles errors during code quality analysis."""
    file_path = tmp_path / "test_file.py"
    file_path.write_text("Test code")
    documenter.logger.exception = MagicMock()
    results = documenter._analyze_code_quality(file_path)
    assert results == {"flake8": [], "ruff": []}
    documenter.logger.exception.assert_called_once()


def test_analyze_directory_structure(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that _analyze_directory_structure checks directory structure against project conventions."""
    (tmp_path / "src" / "dewey" / "core").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ui" / "screens").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "extra_dir").mkdir(exist_ok=True)
    (tmp_path / "src" / "dewey" / "core" / "file1.py").write_text("")
    (tmp_path / "ui" / "screens" / "file2.py").write_text("")
    (tmp_path / "config" / "file3.yaml").write_text("")
    (tmp_path / "tests" / "test_file.py").write_text("")
    (tmp_path / "docs" / "doc.md").write_text("")
    (tmp_path / "extra_dir" / "extra_file.txt").write_text("")

    analysis = documenter._analyze_directory_structure()
    structure = analysis["structure"]
    deviations = analysis["deviations"]

    assert "src/dewey/core" in structure
    assert "ui/screens" in structure
    assert "config" in structure
    assert "tests" in structure
    assert "docs" in structure
    assert "extra_dir" in structure

    assert structure["src/dewey/core"]["expected"] is True
    assert structure["ui/screens"]["expected"] is True
    assert structure["config"]["expected"] is True
    assert structure["tests"]["expected"] is True
    assert structure["docs"]["expected"] is True
    assert structure["extra_dir"]["expected"] is False

    assert "extra_dir" in deviations


def test_generate_readme(documenter: DirectoryDocumenter, tmp_path: Path) -> None:
    """Test that generate_readme generates a comprehensive README with quality and structure analysis."""
    analysis_results = {"file1.py": "Analysis 1", "file2.py": "Analysis 2"}
    dir_analysis = documenter._analyze_directory_structure()
    readme_content = documenter.generate_readme(tmp_path, analysis_results)
    assert "#" in readme_content
    assert "Code Analysis" in readme_content
    assert "Directory Structure" in readme_content


@patch("dewey.core.architecture.document_directory.generate_content")
def test_correct_code_style(mock_generate_content: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that correct_code_style corrects the code style of the given code using an LLM."""
    mock_generate_content.return_value = "Corrected code"
    code = "Test code"
    corrected_code = documenter.correct_code_style(code)
    assert corrected_code == "Corrected code"
    mock_generate_content.assert_called_once()


@patch("dewey.core.architecture.document_directory.generate_content", side_effect=Exception("LLM failed"))
def test_correct_code_style_error(mock_generate_content: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that correct_code_style handles errors when correcting code style."""
    code = "Test code"
    documenter.logger.exception = MagicMock()
    with pytest.raises(Exception):
        documenter.correct_code_style(code)
    documenter.logger.exception.assert_called_once()


@patch("dewey.core.architecture.document_directory.generate_content")
def test_suggest_filename(mock_generate_content: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that suggest_filename suggests a more human-readable filename for the given code using an LLM."""
    mock_generate_content.return_value = "suggested_filename"
    code = "Test code"
    suggested_filename = documenter.suggest_filename(code)
    assert suggested_filename == "suggested_filename"
    mock_generate_content.assert_called_once()


@patch("dewey.core.architecture.document_directory.generate_content", side_effect=Exception("LLM failed"))
def test_suggest_filename_error(mock_generate_content: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that suggest_filename handles errors when suggesting a filename."""
    code = "Test code"
    documenter.logger.exception = MagicMock()
    suggested_filename = documenter.suggest_filename(code)
    assert suggested_filename is None
    documenter.logger.exception.assert_called_once()


@patch("os.listdir")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter._is_checkpointed")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter.analyze_code")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter.suggest_filename")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter.correct_code_style")
@patch("builtins.input", return_value="n")  # Mock user input to skip actions
def test_process_directory(
    mock_input: MagicMock,
    mock_correct_code_style: MagicMock,
    mock_suggest_filename: MagicMock,
    mock_analyze_code: MagicMock,
    mock_is_checkpointed: MagicMock,
    mock_listdir: MagicMock,
    documenter: DirectoryDocumenter,
    tmp_path: Path,
) -> None:
    """Test that process_directory processes the given directory, analyzes its contents, and generates a README.md file."""
    # Setup mocks
    mock_listdir.return_value = ["test_file.py"]
    mock_is_checkpointed.return_value = False
    mock_analyze_code.return_value = ("Analysis", "core.module")
    mock_suggest_filename.return_value = "new_filename"
    mock_correct_code_style.return_value = "Corrected code"

    # Create a test file
    test_file_path = tmp_path / "test_file.py"
    test_file_path.write_text("Test code")

    # Run the process_directory method
    documenter.process_directory(str(tmp_path))

    # Assertions
    mock_listdir.assert_called_once()
    mock_is_checkpointed.assert_called_once()
    mock_analyze_code.assert_called_once()
    mock_suggest_filename.assert_called_once()
    mock_correct_code_style.assert_not_called()  # Because user input is "n"

    # Check that README.md was created
    readme_path = tmp_path / "README.md"
    assert readme_path.exists()


@patch("os.walk")
def test_run(mock_os_walk: MagicMock, documenter: DirectoryDocumenter) -> None:
    """Test that run processes the entire project directory."""
    mock_os_walk.return_value = [("/root", [], [])]
    documenter.process_directory = MagicMock()
    documenter.run()
    documenter.process_directory.assert_called_once_with("/root")


@patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(directory="."))
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter.execute")
def test_main(mock_execute: MagicMock, mock_parse_args: MagicMock) -> None:
    """Test the main execution block."""
    with patch("dewey.core.architecture.document_directory.DirectoryDocumenter") as MockDocumenter:
        # Call the main block
        documenter = MockDocumenter.return_value
        documenter.execute = MagicMock()
        from dewey.core.architecture import document_directory
        document_directory.main()
        # Assertions
        MockDocumenter.assert_called_once_with(root_dir=".")
        documenter.execute.assert_called_once()
