"""Tests to verify that scripts comply with configuration requirements."""

import ast
import inspect
import os
import logging
import sys
import importlib.util
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from typing import List, Set

# Add project root to Python path
project_root = Path("/Users/srvo/dewey")
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Mock dependencies
sys.modules['dewey.utils'] = MagicMock()
sys.modules['dewey.llm.llm_utils'] = MagicMock()
sys.modules['dewey.core.engines'] = MagicMock()

# Import base script directly
base_script_path = project_root / "src/dewey/core/base_script.py"
if not base_script_path.exists():
    raise FileNotFoundError(f"Could not find base_script.py at {base_script_path}")

spec = importlib.util.spec_from_file_location("base_script", base_script_path)
base_script = importlib.util.module_from_spec(spec)
sys.modules["base_script"] = base_script
spec.loader.exec_module(base_script)
BaseScript = base_script.BaseScript

# Import config directly
config_path = project_root / "config/dewey.yaml"
if not config_path.exists():
    config_path = project_root / "src/dewey/config/dewey.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Could not find dewey.yaml in expected locations")

import yaml
with open(config_path, "r") as f:
    config_data = yaml.safe_load(f)

def get_all_python_files() -> List[Path]:
    """Get all Python files in the project."""
    python_files = []
    for root, _, files in os.walk(src_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def is_script_file(file_path: Path) -> bool:
    """Check if a file is a script file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            tree = ast.parse(content)
            
            # Check for if __name__ == '__main__' pattern
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    test = node.test
                    if (isinstance(test, ast.Compare) and
                        isinstance(test.left, ast.Name) and test.left.id == '__name__' and
                        isinstance(test.ops[0], ast.Eq) and
                        isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value == '__main__'):
                        return True
    except:
        pass
    return False

def get_script_classes(file_path: Path) -> Set[str]:
    """Get all script classes in a file that inherit from BaseScript."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            tree = ast.parse(content)
            
            script_classes = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'BaseScript':
                            script_classes.add(node.name)
            return script_classes
    except:
        return set()

def test_scripts_inherit_from_base():
    """Test that all scripts inherit from BaseScript."""
    script_files = [f for f in get_all_python_files() if is_script_file(f)]
    non_compliant = []

    for script_file in script_files:
        if script_file.name == 'base_script.py':
            continue

        script_classes = get_script_classes(script_file)
        if not script_classes:
            non_compliant.append(str(script_file))

    if non_compliant:
        pytest.fail(f"The following scripts do not inherit from BaseScript:\n" +
                   "\n".join(non_compliant))

def test_scripts_use_config_logging():
    """Test that scripts use logging configuration from dewey.yaml."""
    script_files = [f for f in get_all_python_files() if is_script_file(f)]
    non_compliant = []

    for script_file in script_files:
        try:
            with open(script_file, 'r') as f:
                content = f.read()
                tree = ast.parse(content)

                # Check for direct logging configuration
                has_basic_config = False
                has_direct_handler = False

                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            if node.func.attr == 'basicConfig' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'logging':
                                has_basic_config = True
                        if isinstance(node.func, ast.Name) and node.func.id in ['FileHandler', 'StreamHandler']:
                            has_direct_handler = True

                if has_basic_config or has_direct_handler:
                    non_compliant.append(str(script_file))
        except:
            continue

    if non_compliant:
        pytest.fail(f"The following scripts configure logging directly instead of using dewey.yaml:\n" +
                   "\n".join(non_compliant))

def test_scripts_use_config_paths():
    """Test that scripts use paths from dewey.yaml."""
    script_files = [f for f in get_all_python_files() if is_script_file(f)]
    non_compliant = []

    for script_file in script_files:
        try:
            with open(script_file, 'r') as f:
                content = f.read()
                tree = ast.parse(content)

                # Check for hardcoded paths
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        path = node.value
                        if any(path.startswith(prefix) for prefix in ['/', '~/', './']):
                            if not any(path.startswith(ignore) for ignore in ['/opt', '/usr', '/bin', '/etc']):
                                non_compliant.append(str(script_file))
                                break
        except:
            continue

    if non_compliant:
        pytest.fail(f"The following scripts use hardcoded paths instead of config:\n" +
                   "\n".join(non_compliant))

def test_scripts_use_config_settings():
    """Test that scripts use settings from dewey.yaml."""
    script_files = [f for f in get_all_python_files() if is_script_file(f)]
    non_compliant = []

    for script_file in script_files:
        try:
            with open(script_file, 'r') as f:
                content = f.read()
                tree = ast.parse(content)

                # Check for hardcoded settings
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id.upper()
                                if name.endswith('_URL') or name.endswith('_KEY') or name.endswith('_TOKEN'):
                                    if isinstance(node.value, ast.Constant):
                                        non_compliant.append(str(script_file))
                                        break
        except:
            continue

    if non_compliant:
        pytest.fail(f"The following scripts use hardcoded settings instead of config:\n" +
                   "\n".join(non_compliant))

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = {
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'paths': {
            'data': 'data',
            'logs': 'logs',
            'config': 'config'
        },
        'settings': {
            'default_llm': 'gpt-4',
            'default_db': 'motherduck'
        }
    }

    # Create a mock for dewey.utils.load_config that returns our config dict
    mock_load_config = MagicMock(return_value=config)

    with patch('base_script.load_config', mock_load_config), \
         patch('dewey.utils.load_config', mock_load_config), \
         patch('dewey.utils.setup_logging', return_value=logging.getLogger('test_script')), \
         patch('dewey.utils.get_logger', return_value=logging.getLogger('test_script')), \
         patch('dewey.llm.llm_utils.get_llm_client', return_value=None), \
         patch('dewey.core.engines.MotherDuckEngine', return_value=None):
        yield config

@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    yield
    root_logger.handlers = []

@pytest.fixture(autouse=True)
def mock_args():
    """Mock command line arguments for testing."""
    with patch('sys.argv', ['test_script']):
        yield

def test_base_script_logging_setup(mock_args, mock_config):
    """Test that BaseScript properly sets up logging using dewey.yaml config."""
    test_script = BaseScript(name="test_script")
    test_script.initialize()

    # Check that logging is configured according to dewey.yaml
    assert logging.getLogger().level == logging.INFO

def test_base_script_config_access(mock_args, mock_config):
    """Test that BaseScript can access all required config sections."""
    test_script = BaseScript(name="test_script")
    test_script.initialize()

    # Check that all required config sections are accessible
    assert test_script.config.get('logging') is not None
    assert test_script.config.get('paths') is not None
    assert test_script.config.get('settings') is not None 