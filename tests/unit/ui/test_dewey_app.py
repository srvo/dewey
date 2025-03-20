import pytest
from textual.app import App
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from pathlib import Path
from src.dewey.unit/ui.app import DeweyApp, ScriptInfo, ScriptDetails

@pytest.fixture
def setup_test_dirs(tmp_path: Path) -> Path:
    """Fixture to setup temporary directories and files for testing."""
    (tmp_path / "core").mkdir()
    (tmp_path / "utils").mkdir()
    (tmp_path / "scripts").mkdir()
    # Create test files
    (tmp_path / "core/test_core.py").touch()
    (tmp_path / "utils/test_utils.py").touch()
    (tmp_path / "scripts/test_script.py").touch()
    return tmp_path

def test_scan_scripts_populates_tree(setup_test_dirs: Path) -> None:
    """Test that scan_scripts correctly populates the script tree."""
    app = DeweyApp()
    app.action_refresh()  # Triggers scan_scripts
    # Check core modules node
    core_node = app.script_tree.root.children[0]
    assert core_node.label == "Core Modules"
    assert len(core_node.children) == 1
    # Check utils node
    utils_node = app.script_tree.root.children[1]
    assert utils_node.label == "Utilities"
    assert len(utils_node.children) == 1
    # Check scripts node
    scripts_node = app.script_tree.root.children[2]
    assert scripts_node.label == "Management Scripts"
    assert len(scripts_node.children) == 1

def test_node_selection_updates_details(setup_test_dirs: Path) -> None:
    """Test that selecting a node updates the details widget."""
    app = DeweyApp()
    app.action_refresh()
    # Get the first core module node
    core_node = app.script_tree.root.children[0]
    test_core_node = core_node.children[0]
    # Simulate node selection
    event = Tree.NodeSelected(test_core_node)
    app.post_message(event)
    # Check details content
    expected_content = (
        f"# test_core\n"
        f"Type: Core Module\n"
        f"Path: {setup_test_dirs}/core/test_core.py\n\n"
        "## Description\n"
        "No description available.\n\n"
        "## Usage\n"
        "No usage information available."
    )
    assert app.details.script_info.name == "test_core"
    assert app.details.script_info.type == "Core Module"
    assert app.details.content == expected_content

def test_refresh_updates_tree_after_file_addition(setup_test_dirs: Path) -> None:
    """Test that refreshing updates the tree after new files are added."""
    app = DeweyApp()
    app.action_refresh()
    # Add new file
    new_file_path = setup_test_dirs / "core/new_script.py"
    new_file_path.touch()
    app.action_refresh()
    # Check new node exists
    core_node = app.script_tree.root.children[0]
    new_node_labels = [child.label for child in core_node.children]
    assert "new_script (Core Module)" in new_node_labels

def test_ignores_hidden_files(setup_test_dirs: Path) -> None:
    """Test that files starting with '_' are ignored."""
    hidden_file = setup_test_dirs / "core/_hidden.py"
    hidden_file.touch()
    app = DeweyApp()
    app.action_refresh()
    core_node = app.script_tree.root.children[0]
    assert len(core_node.children) == 1  # Only test_core.py remains
