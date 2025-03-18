import pytest
import logging
import yaml
from pathlib import Path
from src.dewey.core.base_script import BaseScript

# Configure logging from central config
config_path = Path(__file__).parent.parent / "config/dewey.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

logging.basicConfig(
    format=config["logging"]["format"],
    datefmt=config["logging"]["datefmt"],
    level=config["logging"]["level"],
)

@pytest.fixture(autouse=True)
def clean_logging(caplog):
    """Ensure logs are cleared between tests."""
    caplog.clear()

@pytest.fixture
def base_script():
    """Fixture providing BaseScript instance for test setup"""
    class TestScript(BaseScript):
        def __init__(self):
            super().__init__(config_section="test")
    return TestScript()
