import pytest
from src.api_manager import add_new_api, reset_query_counts, api_config
from datetime import datetime, timedelta
import logging

def test_add_new_api_valid():
    """Test adding a valid new API."""
    add_new_api(
        name="TestAPI",
        endpoint="https://api.test.com",
        rate_limit=100,
        api_key="test_key",
        description="Test API",
        use_cases=["testing"],
        capabilities=["test"]
    )
    assert "TestAPI" in api_config

def test_add_new_api_invalid():
    """Test adding an invalid API."""
    with pytest.raises(ValueError):
        add_new_api(
            name="",
            endpoint="invalid",
            rate_limit=-1,
            api_key="",
            description="",
            use_cases=[123],
            capabilities=[456]
        )

def test_reset_query_counts():
    """Test resetting query counts."""
    # Set up test data
    api_name = "TestAPI"
    api_config[api_name] = {
        "queries_made": 10,
        "last_reset": datetime.now() - timedelta(days=2),
        "rate_limit": 100
    }
    
    reset_query_counts()
    assert api_config[api_name]["queries_made"] == 0

def test_reset_query_counts_error(caplog):
    """Test error handling in reset_query_counts."""
    # Create invalid config
    api_name = "BadAPI"
    api_config[api_name] = {}
    
    reset_query_counts()
    assert "Invalid configuration for API" in caplog.text
