"""A simple test to verify that the test framework is working."""

import pytest
import sys
from pathlib import Path

def test_python_version():
    """Test that Python version is available."""
    assert sys.version is not None
    assert sys.version_info.major == 3

def test_paths_exist():
    """Test that important paths exist."""
    # Project root
    project_root = Path(__file__).parent.parent.parent
    assert project_root.exists()
    
    # Source directory
    src_dir = project_root / "src"
    assert src_dir.exists()
    
    # Dewey core module
    core_dir = project_root / "src" / "dewey" / "core"
    assert core_dir.exists()

def test_dewey_imports():
    """Test that basic dewey imports work."""
    # Import basic modules to check imports work
    try:
import dewey
        assert dewey.__name__ == "dewey"
    except ImportError:
        # If it can't be imported directly, add src to path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
import dewey
        assert dewey.__name__ == "dewey" 