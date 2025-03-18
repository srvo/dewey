import pytest
from dewey.core.base_script import BaseScript

class TestUtils(BaseScript):
    """Test utilities for CRM module with base script configuration"""

    def __init__(self):
        super().__init__(config_section='test_utils')

@pytest.fixture
def mock_motherduck_env_vars(monkeypatch):
    """Mock MotherDuck environment variables for testing (with logging)

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest fixture for environment patches

    Returns:
        None
    """
    try:
        self.logger.info("Setting up MotherDuck mock environment")
        monkeypatch.setenv("MOTHERDUCK_API_KEY", "test_key")
        monkeypatch.setenv("MOTHERDUCK_ORG", "test_org")
    except Exception as e:
        self.logger.error(f"Mock setup failed: {str(e)}")
        raise
