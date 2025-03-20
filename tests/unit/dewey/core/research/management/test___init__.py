import pytest

# Import the module to be tested
from dewey.core.research import management
from dewey.core.base_script import BaseScript


def test_module_import():
    """Test that the module can be imported without errors."""
    assert management is not None


def test_base_script_inheritance():
    """Test that a class within the module can inherit from BaseScript."""

    class MockResearchScript(BaseScript):
        def __init__(self):
            super().__init__(config_section='test_config')

        def run(self):
            pass

    script = MockResearchScript()
    assert isinstance(script, BaseScript)
    assert script.config_section == 'test_config'


def test_base_script_config_loading():
    """Test that the BaseScript can load configuration."""

    class MockResearchScript(BaseScript):
        def __init__(self):
            super().__init__(config_section='test_config')

        def run(self):
            pass

    script = MockResearchScript()
    assert script.config is not None
    assert isinstance(script.config, dict)
    assert 'local_db_path' in script.config


def test_base_script_logging():
    """Test that the BaseScript has a logger."""

    class MockResearchScript(BaseScript):
        def __init__(self):
            super().__init__()

        def run(self):
            pass

    script = MockResearchScript()
    assert script.logger is not None

