```python
import os
from typing import Any, Dict

import pytest

pytest_plugins = ["dbt.tests.fixtures.project"]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Adds command-line options for specifying the profile type."""
    parser.addoption("--profile", action="store", default="postgres", type=str)


def pytest_configure(config: pytest.Config) -> None:
    """Configures pytest with custom markers for skipping and only running tests
    based on profile.
    """
    config.addinivalue_line(
        "markers",
        "skip_profile(profile): skip test for the given profile",
    )
    config.addinivalue_line(
        "markers",
        "only_profile(profile): only test the given profile",
    )


def _get_target_config(profile_type: str) -> Dict[str, Any]:
    """Returns the target configuration based on the specified profile type.

    Args:
        profile_type: The type of profile to retrieve the target configuration for.

    Returns:
        A dictionary containing the target configuration.

    Raises:
        ValueError: If the profile type is invalid.
    """
    if profile_type == "postgres":
        return _postgres_target()
    if profile_type == "redshift":
        return _redshift_target()
    if profile_type == "snowflake":
        return _snowflake_target()
    if profile_type == "bigquery":
        return _bigquery_target()
    raise ValueError(f"Invalid profile type '{profile_type}'")


def _postgres_target() -> Dict[str, Any]:
    """Returns the target configuration for Postgres."""
    return {
        "type": "postgres",
        "host": os.getenv("POSTGRES_TEST_HOST"),
        "user": os.getenv("POSTGRES_TEST_USER"),
        "pass": os.getenv("POSTGRES_TEST_PASS"),
        "port": int(os.getenv("POSTGRES_TEST_PORT")),
        "dbname": os.getenv("POSTGRES_TEST_DBNAME"),
    }


def _redshift_target() -> Dict[str, Any]:
    """Returns the target configuration for Redshift."""
    return {
        "type": "redshift",
        "host": os.getenv("REDSHIFT_TEST_HOST"),
        "user": os.getenv("REDSHIFT_TEST_USER"),
        "pass": os.getenv("REDSHIFT_TEST_PASS"),
        "port": int(os.getenv("REDSHIFT_TEST_PORT")),
        "dbname": os.getenv("REDSHIFT_TEST_DBNAME"),
    }


def _bigquery_target() -> Dict[str, Any]:
    """Returns the target configuration for BigQuery."""
    return {
        "type": "bigquery",
        "method": "service-account",
        "keyfile": os.getenv("BIGQUERY_SERVICE_KEY_PATH"),
        "project": os.getenv("BIGQUERY_TEST_DATABASE"),
    }


def _snowflake_target() -> Dict[str, Any]:
    """Returns the target configuration for Snowflake."""
    return {
        "type": "snowflake",
        "account": os.getenv("SNOWFLAKE_TEST_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_TEST_USER"),
        "password": os.getenv("SNOWFLAKE_TEST_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_TEST_ROLE"),
        "database": os.getenv("SNOWFLAKE_TEST_DATABASE"),
        "warehouse": os.getenv("SNOWFLAKE_TEST_WAREHOUSE"),
    }


@pytest.fixture(scope="session")
def dbt_profile_target(request: pytest.FixtureRequest) -> Dict[str, Any]:
    """Fixture to provide the dbt profile target configuration.

    Returns:
        A dictionary representing the dbt profile target.
    """
    profile_type = request.config.getoption("--profile")
    return _get_target_config(profile_type)


@pytest.fixture(autouse=True)
def skip_by_profile_type(request: pytest.FixtureRequest) -> None:
    """Fixture to skip tests based on the 'skip_profile' marker."""
    profile_type = request.config.getoption("--profile")
    marker = request.node.get_closest_marker("skip_profile")
    if marker:
        for skip_profile_type in marker.args:
            if skip_profile_type == profile_type:
                pytest.skip(f"skipped on '{profile_type}' profile")


@pytest.fixture(autouse=True)
def only_profile_type(request: pytest.FixtureRequest) -> None:
    """Fixture to only run tests based on the 'only_profile' marker."""
    profile_type = request.config.getoption("--profile")
    marker = request.node.get_closest_marker("only_profile")
    if marker:
        for only_profile_type in marker.args:
            if only_profile_type != profile_type:
                pytest.skip(f"skipped on '{profile_type}' profile")
```
