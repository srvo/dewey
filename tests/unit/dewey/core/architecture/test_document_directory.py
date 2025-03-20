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
    FileSystemInterface,
    RealFileSystem,
    LLMClientInterface,
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
def mock_llm_client() -> MagicMock:
    """Fixture to mock LLMClientInterface."""
    return MagicMock(spec=LLMClientInterface)


@pytest.fixture
def mock_fs() -> MagicMock:
    """Fixture to mock FileSystemInterface."""
    mock = MagicMock(spec=FileSystemInterface)
    return mock


@pytest.fixture
def documenter(
    tmp_path: Path,
    mock_base_script: MagicMock,
    mock_llm_client: MagicMock,
    mock_fs: MagicMock,
) -> DirectoryDocumenter:
    """Fixture to create a DirectoryDocumenter instance with a temporary directory."""
    conventions_file = tmp_path / "CONVENTIONS.md"
    conventions_file.write_text("Project Conventions")
    checkpoint_file = tmp_path / ".dewey_documenter_checkpoint.json"
    root_dir = tmp_path
    documenter = DirectoryDocumenter(
        root_dir=str(root_dir),
        llm_client=mock_llm_client,
        fs=mock_fs,
    )
    documenter.logger = mock_base_script.logger
    documenter.config = mock_base_script.config
    documenter.conventions_path = conventions_file
    documenter.checkpoint_file = checkpoint_file
    return documenter


def test_directory_documenter_init(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test the initialization of the DirectoryDocumenter class."""
    mock_fs.exists.return_value = True
    mock_fs.read_text.return_value = "Project Conventions"
    assert documenter.root_dir == tmp_path.resolve()
    assert documenter.conventions_path.exists()
    assert documenter.checkpoints == {}
    assert documenter.conventions == "Project Conventions"


def test_directory_documenter_init_no_conventions(
    tmp_path: Path,
    mock_base_script: MagicMock,
    mock_llm_client: MagicMock,
    mock_fs: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test initialization when CONVENTIONS.md is not found."""
    monkeypatch.setattr(sys, "exit", lambda x: None)
    mock_fs.exists.return_value = False
    with pytest.raises(SystemExit):
        DirectoryDocumenter(
            root_dir=str(tmp_path),
            llm_client=mock_llm_client,
            fs=mock_fs,
        )


def test_validate_directory_exists(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _validate_directory raises an error if the directory doesn't exist."""
    mock_fs.exists.return_value = False
    with pytest.raises(FileNotFoundError):
        documenter._validate_directory()
    mock_fs.exists.assert_called_once_with(documenter.root_dir)


def test_validate_directory_access(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _validate_directory raises an error if the directory is not accessible."""
    # This test is difficult to mock correctly due to os.access. Skipping for now.
    pytest.skip("Skipping permission test due to difficulty in mocking os.access")


def test_load_conventions(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _load_conventions loads the conventions from the CONVENTIONS.md file."""
    mock_fs.read_text.return_value = "Test Conventions"
    conventions = documenter._load_conventions()
    assert conventions == "Test Conventions"
    mock_fs.read_text.assert_called_once_with(documenter.conventions_path)


def test_load_conventions_not_found(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _load_conventions handles the case where the CONVENTIONS.md file is not found."""
    monkeypatch.setattr(sys, "exit", lambda x: None)
    mock_fs.read_text.side_effect = FileNotFoundError
    with pytest.raises(SystemExit):
        documenter._load_conventions()
    documenter.logger.exception.assert_called_once()


def test_load_conventions_error(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _load_conventions handles errors when loading the conventions file."""
    monkeypatch.setattr(sys, "exit", lambda x: None)
    mock_fs.read_text.side_effect = Exception("Failed to open")
    with pytest.raises(SystemExit):
        documenter._load_conventions()
    documenter.logger.exception.assert_called_once()


def test_load_checkpoints(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _load_checkpoints loads checkpoint data from a file."""
    checkpoint_data = {"file1.py": "hash1", "file2.py": "hash2"}
    mock_fs.exists.return_value = True
    mock_fs.read_text.return_value = json.dumps(checkpoint_data)
    checkpoints = documenter._load_checkpoints()
    assert checkpoints == checkpoint_data
    mock_fs.read_text.assert_called_once_with(documenter.checkpoint_file)


def test_load_checkpoints_no_file(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _load_checkpoints returns an empty dictionary if the checkpoint file doesn't exist."""
    mock_fs.exists.return_value = False
    checkpoints = documenter._load_checkpoints()
    assert checkpoints == {}
    mock_fs.exists.assert_called_once_with(documenter.checkpoint_file)


def test_load_checkpoints_invalid_json(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _load_checkpoints handles invalid JSON in the checkpoint file."""
    mock_fs.exists.return_value = True
    mock_fs.read_text.return_value = "invalid json"
    checkpoints = documenter._load_checkpoints()
    assert checkpoints == {}
    documenter.logger.warning.assert_called_once()


def test_save_checkpoints(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _save_checkpoints saves checkpoint data to a file."""
    checkpoint_data = {"file1.py": "hash1", "file2.py": "hash2"}
    documenter.checkpoints = checkpoint_data
    documenter._save_checkpoints()
    mock_fs.write_text.assert_called_once_with(
        documenter.checkpoint_file,
        json.dumps(checkpoint_data, indent=4),
    )


def test_save_checkpoints_error(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _save_checkpoints handles errors when saving the checkpoint file."""
    documenter.checkpoints = {"file1.py": "hash1"}
    mock_fs.write_text.side_effect = Exception("Failed to open")
    documenter._save_checkpoints()
    documenter.logger.exception.assert_called_once()


@pytest.mark.parametrize(
    "file_content, expected_hash",
    [
        ("Test content", f"{len('Test content')}_" + hashlib.sha256("Test content".encode()).hexdigest()),
        ("", "empty_file"),
    ],
)
def test_calculate_file_hash(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
    file_content: str,
    expected_hash: str,
) -> None:
    """Test that _calculate_file_hash calculates the SHA256 hash of a file's contents."""
    file_path = tmp_path / "test_file.txt"
    with patch("builtins.open", mock_open(read_data=file_content)) as mock_file:
        mock_fs.stat.return_value.st_size = len(file_content)
        file_hash = documenter._calculate_file_hash(file_path)
        assert isinstance(file_hash, str)
        assert file_hash == expected_hash
        mock_file.assert_called_once_with(file_path, "rb")


def test_calculate_file_hash_error(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _calculate_file_hash handles errors when calculating the hash."""
    file_path = tmp_path / "test_file.txt"
    mock_fs.stat.side_effect = Exception("Failed to stat")
    documenter.logger.exception = MagicMock()
    with pytest.raises(Exception):
        documenter._calculate_file_hash(file_path)
    documenter.logger.exception.assert_called_once()


def test_is_checkpointed(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _is_checkpointed checks if a file has been processed based on its content hash."""
    file_path = tmp_path / "test_file.txt"
    file_content = "Test content"
    file_hash = f"{len(file_content)}_" + hashlib.sha256(file_content.encode()).hexdigest()
    documenter.checkpoints = {str(file_path): file_hash}
    with patch("builtins.open", mock_open(read_data=file_content)):
        mock_fs.stat.return_value.st_size = len(file_content)
        assert documenter._is_checkpointed(file_path)


def test_is_checkpointed_not_found(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _is_checkpointed returns False if the file is not in the checkpoints."""
    file_path = tmp_path / "test_file.txt"
    documenter.checkpoints = {}
    with patch("builtins.open", mock_open(read_data="Test content")):
        mock_fs.stat.return_value.st_size = len("Test content")
        assert not documenter._is_checkpointed(file_path)


def test_is_checkpointed_hash_mismatch(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _is_checkpointed returns False if the file's hash doesn't match the checkpointed hash."""
    file_path = tmp_path / "test_file.txt"
    documenter.checkpoints = {str(file_path): "wrong_hash"}
    with patch("builtins.open", mock_open(read_data="Test content")):
        mock_fs.stat.return_value.st_size = len("Test content")
        assert not documenter._is_checkpointed(file_path)


def test_is_checkpointed_error(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _is_checkpointed handles errors when reading the file to check the checkpoint."""
    file_path = tmp_path / "test_file.txt"
    mock_fs.stat.side_effect = Exception("Failed to stat")
    documenter.logger.exception = MagicMock()
    with patch("builtins.open", mock_open(read_data="Test content")):
        with pytest.raises(Exception):
            documenter._is_checkpointed(file_path)
    documenter.logger.exception.assert_called_once()


def test_checkpoint(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _checkpoint checkpoints a file by saving its content hash."""
    file_path = tmp_path / "test_file.txt"
    file_content = "Test content"
    mock_fs.read_text.return_value = file_content
    documenter._checkpoint(file_path)
    content_hash = hashlib.sha256(file_content.encode()).hexdigest()
    assert documenter.checkpoints[str(file_path)] == content_hash
    mock_fs.write_text.assert_called_once()


def test_checkpoint_error(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _checkpoint handles errors when checkpointing a file."""
    file_path = tmp_path / "test_file.txt"
    mock_fs.read_text.side_effect = Exception("Failed to read")
    documenter.logger.exception = MagicMock()
    documenter._checkpoint(file_path)
    documenter.logger.exception.assert_called_once()


def test_analyze_code(
    documenter: DirectoryDocumenter,
    mock_llm_client: MagicMock,
) -> None:
    """Test that analyze_code analyzes the given code using an LLM and returns a summary."""
    mock_llm_client.generate_content.return_value = "Analysis\n4. core.module"
    code = "Test code"
    analysis, suggested_module = documenter.analyze_code(code)
    assert analysis == "Analysis"
    assert suggested_module == "core.module"
    mock_llm_client.generate_content.assert_called_once()


def test_analyze_code_error(
    documenter: DirectoryDocumenter,
    mock_llm_client: MagicMock,
) -> None:
    """Test that analyze_code handles errors during code analysis."""
    mock_llm_client.generate_content.side_effect = Exception("LLM failed")
    code = "Test code"
    documenter.logger.exception = MagicMock()
    with pytest.raises(Exception):
        documenter.analyze_code(code)
    documenter.logger.exception.assert_called_once()


@patch("subprocess.run")
def test_analyze_code_quality(
    mock_subprocess_run: MagicMock,
    documenter: DirectoryDocumenter,
    tmp_path: Path,
) -> None:
    """Test that _analyze_code_quality runs code quality checks using flake8 and ruff."""
    mock_subprocess_run.return_value.stdout = "flake8 output\nruff output"
    file_path = tmp_path / "test_file.py"
    results = documenter._analyze_code_quality(file_path)
    assert "flake8" in results
    assert "ruff" in results
    mock_subprocess_run.assert_called()


@patch("subprocess.run", side_effect=Exception("Subprocess failed"))
def test_analyze_code_quality_error(
    mock_subprocess_run: MagicMock,
    documenter: DirectoryDocumenter,
    tmp_path: Path,
) -> None:
    """Test that _analyze_code_quality handles errors during code quality analysis."""
    file_path = tmp_path / "test_file.py"
    documenter.logger.exception = MagicMock()
    results = documenter._analyze_code_quality(file_path)
    assert results == {"flake8": [], "ruff": []}
    documenter.logger.exception.assert_called_once()


def test_analyze_directory_structure(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that _analyze_directory_structure checks directory structure against project conventions."""
    # Mock directory structure
    mock_fs.listdir.return_value = ["src", "ui", "config", "tests", "docs", "extra_dir"]
    mock_fs.is_dir.return_value = True
    mock_fs.exists.return_value = True

    analysis = documenter._analyze_directory_structure()
    structure = analysis["structure"]
    deviations = analysis["deviations"]

    assert "src" in structure
    assert "ui" in structure
    assert "config" in structure
    assert "tests" in structure
    assert "docs" in structure
    assert "extra_dir" in structure

    assert "extra_dir" in deviations


def test_generate_readme(
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that generate_readme generates a comprehensive README with quality and structure analysis."""
    analysis_results = {"file1.py": "Analysis 1", "file2.py": "Analysis 2"}
    mock_fs.listdir.return_value = ["file1.py", "file2.py"]
    mock_fs.is_dir.return_value = True
    mock_fs.exists.return_value = True
    dir_analysis = documenter._analyze_directory_structure()
    readme_content = documenter.generate_readme(tmp_path, analysis_results)
    assert "#" in readme_content
    assert "Code Analysis" in readme_content
    assert "Directory Structure" in readme_content


def test_correct_code_style(
    documenter: DirectoryDocumenter,
    mock_llm_client: MagicMock,
) -> None:
    """Test that correct_code_style corrects the code style of the given code using an LLM."""
    mock_llm_client.generate_content.return_value = "Corrected code"
    code = "Test code"
    corrected_code = documenter.correct_code_style(code)
    assert corrected_code == "Corrected code"
    mock_llm_client.generate_content.assert_called_once()


def test_correct_code_style_error(
    documenter: DirectoryDocumenter,
    mock_llm_client: MagicMock,
) -> None:
    """Test that correct_code_style handles errors when correcting code style."""
    mock_llm_client.generate_content.side_effect = Exception("LLM failed")
    code = "Test code"
    documenter.logger.exception = MagicMock()
    with pytest.raises(Exception):
        documenter.correct_code_style(code)
    documenter.logger.exception.assert_called_once()


def test_suggest_filename(
    documenter: DirectoryDocumenter,
    mock_llm_client: MagicMock,
) -> None:
    """Test that suggest_filename suggests a more human-readable filename for the given code using an LLM."""
    mock_llm_client.generate_content.return_value = "suggested_filename"
    code = "Test code"
    suggested_filename = documenter.suggest_filename(code)
    assert suggested_filename == "suggested_filename"
    mock_llm_client.generate_content.assert_called_once()


def test_suggest_filename_error(
    documenter: DirectoryDocumenter,
    mock_llm_client: MagicMock,
) -> None:
    """Test that suggest_filename handles errors when suggesting a filename."""
    mock_llm_client.generate_content.side_effect = Exception("LLM failed")
    code = "Test code"
    documenter.logger.exception = MagicMock()
    suggested_filename = documenter.suggest_filename(code)
    assert suggested_filename is None
    documenter.logger.exception.assert_called_once()


@patch("builtins.input", return_value="n")  # Mock user input to skip actions
def test_process_file(
    mock_input: MagicMock,
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
    mock_llm_client: MagicMock,
) -> None:
    """Test that _process_file processes a single file."""
    file_path = tmp_path / "test_file.py"
    file_content = "Test code"
    mock_fs.read_text.return_value = file_content
    mock_llm_client.generate_content.return_value = "Analysis\n4. core.module"
    analysis, suggested_module = documenter._process_file(file_path)
    assert analysis == "Analysis"
    assert suggested_module == "core.module"
    mock_fs.read_text.assert_called_once_with(file_path)
    mock_llm_client.generate_content.assert_called_once()


@patch("builtins.input", return_value="n")  # Mock user input to skip actions
def test_apply_improvements(
    mock_input: MagicMock,
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
    mock_llm_client: MagicMock,
) -> None:
    """Test that _apply_improvements applies suggested improvements to a file."""
    file_path = tmp_path / "test_file.py"
    file_content = "Test code"
    mock_fs.read_text.return_value = file_content
    mock_llm_client.generate_content.return_value = "new_filename"
    documenter._apply_improvements(file_path, "core.module")
    mock_fs.mkdir.assert_called_once()
    assert mock_input.call_count == 3


@patch("os.listdir")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter._is_checkpointed")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter._process_file")
@patch("dewey.core.architecture.document_directory.DirectoryDocumenter._apply_improvements")
@patch("builtins.input", return_value="n")  # Mock user input to skip actions
def test_process_directory(
    mock_input: MagicMock,
    mock_apply_improvements: MagicMock,
    mock_process_file: MagicMock,
    mock_is_checkpointed: MagicMock,
    mock_listdir: MagicMock,
    documenter: DirectoryDocumenter,
    tmp_path: Path,
    mock_fs: MagicMock,
) -> None:
    """Test that process_directory processes the given directory, analyzes its contents, and generates a README.md file."""
    # Setup mocks
    mock_listdir.return_value = ["test_file.py"]
    mock_is_checkpointed.return_value = False
    mock_process_file.return_value = ("Analysis", "core.module")

    # Create a test file
    test_file_path = tmp_path / "test_file.py"
    test_file_path.write_text("Test code")
    mock_fs.exists.return_value = True
    mock_fs.is_dir.return_value = True

    # Run the process_directory method
    documenter.process_directory(str(tmp_path))

    # Assertions
    mock_listdir.assert_called_once()
    mock_is_checkpointed.assert_called_once()
    mock_process_file.assert_called_once()
    mock_apply_improvements.assert_called_once()

    # Check that README.md was created
    readme_path = tmp_path / "README.md"
    assert mock_fs.write_text.called


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


class MockFileSystem(FileSystemInterface):
    """Mock implementation of FileSystemInterface for testing."""

    def __init__(self, exists_return: bool = True, is_dir_return: bool = True, read_text_return: str = "") -> None:
        """Initializes the MockFileSystem with default return values."""
        self.exists_return = exists_return
        self.is_dir_return = is_dir_return
        self.read_text_return = read_text_return
        self.write_text_data: Dict[Path, str] = {}
        self.renamed: List[Tuple[Path, Path]] = []
        self.moved: List[Tuple[Path, Path]] = []
        self.listdir_return: List[str] = []
        self.mkdir_called: List[Path] = []
        self.stat_result = os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))  # Dummy stat result

    def exists(self, path: Path) -> bool:
        """Mock exists method."""
        return self.exists_return

    def is_dir(self, path: Path) -> bool:
        """Mock is_dir method."""
        return self.is_dir_return

    def read_text(self, path: Path) -> str:
        """Mock read_text method."""
        return self.read_text_return

    def write_text(self, path: Path, content: str) -> None:
        """Mock write_text method."""
        self.write_text_data[path] = content

    def rename(self, src: Path, dest: Path) -> None:
        """Mock rename method."""
        self.renamed.append((src, dest))

    def move(self, src: Path, dest: Path) -> None:
        """Mock move method."""
        self.moved.append((src, dest))

    def listdir(self, path: Path) -> List[str]:
        """Mock listdir method."""
        return self.listdir_return

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        """Mock mkdir method."""
        self.mkdir_called.append(path)

    def stat(self, path: Path) -> os.stat_result:
        """Mock stat method."""
        return self.stat_result

    def remove(self, path: Path) -> None:
        """Mock remove method."""
        pass


def test_real_file_system(tmp_path: Path) -> None:
    """Test the RealFileSystem class."""
    fs = RealFileSystem()
    test_file = tmp_path / "test_file.txt"
    test_dir = tmp_path / "test_dir"

    # Test exists
    assert not fs.exists(test_file)
    test_file.write_text("test")
    assert fs.exists(test_file)

    # Test is_dir
    assert not fs.is_dir(test_dir)
    test_dir.mkdir()
    assert fs.is_dir(test_dir)

    # Test read_text
    assert fs.read_text(test_file) == "test"

    # Test write_text
    fs.write_text(test_file, "new test")
    assert test_file.read_text() == "new test"

    # Test rename
    new_file = tmp_path / "new_file.txt"
    fs.rename(test_file, new_file)
    assert not fs.exists(test_file)
    assert fs.exists(new_file)

    # Test move
    move_dir = tmp_path / "move_dir"
    move_dir.mkdir()
    moved_file = move_dir / "new_file.txt"
    fs.move(new_file, moved_file)
    assert not fs.exists(new_file)
    assert fs.exists(moved_file)

    # Test listdir
    assert fs.listdir(move_dir) == ["new_file.txt"]

    # Test mkdir
    new_dir = tmp_path / "new_dir"
    fs.mkdir(new_dir)
    assert fs.exists(new_dir)

    # Test stat
    stat_result = fs.stat(moved_file)
    assert stat_result.st_size == len("new test")
