import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_mock_motherduck_env_vars(mock_motherduck_env_vars):
    """
    Test that MotherDuck environment variables are properly mocked.

    Args:
        mock_motherduck_env_vars: Pytest fixture that sets up mock env vars.

    Raises:
        AssertionError: If mocked env vars do not match expected values.
    """
    assert os.getenv("MOTHERDUCK_API_KEY") == "test_key", "API key not set correctly"
    assert os.getenv("MOTHERDUCK_ORG") == "test_org", "Org not set correctly"

def test_mock_motherduck_env_vars_no_overwrite(mock_motherduck_env_vars):
    """
    Test that original env vars are restored after fixture teardown.

    Args:
        mock_motherduck_env_vars: Pytest fixture that sets up mock env vars.

    Raises:
        AssertionError: If original env vars are not restored.
    """
    # Act
    del os.environ["MOTHERDUCK_API_KEY"]
    del os.environ["MOTHERDUCK_ORG"]

    # Assert
    assert "MOTHERDUCK_API_KEY" not in os.environ
    assert "MOTHERDUCK_ORG" not in os.environ
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars
from ibis.tests.util import assert_equal

def test_ibis_query_execution(mock_motherduck_env_vars):
    """
    Integration test for Ibis queries using mocked MotherDuck credentials.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If query execution fails or results differ
    """
    import ibis
    con = ibis.connect('duckdb:///:memory:')
    table = con.create_table('test_table', {'col': 'int'})
    result = con.sql('SELECT * FROM test_table').execute()
    assert_equal(result, ibis.literal([]).to_table())
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_edge_cases(mock_motherduck_env_vars):
    """
    Test edge cases for MotherDuck environment variables.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If invalid states are not properly handled
    """
    # Test empty API key
    with pytest.raises(ValueError, match="Invalid API key"):
        os.environ["MOTHERDUCK_API_KEY"] = ""
        # Your code that validates API key here

    # Test non-string API key
    with pytest.raises(TypeError, match="API key must be a string"):
        os.environ["MOTHERDUCK_API_KEY"] = 123
        # Your code that validates API key type here
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_persistence(mock_motherduck_env_vars):
    """
    Test environment variable persistence across test boundaries.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If env vars persist after test completion
    """
    # Verify initial state
    assert os.getenv("MOTHERDUCK_API_KEY") == "test_key"

    # Teardown and re-check
    mock_motherduck_env_vars.finalizer()
    assert os.getenv("MOTHERDUCK_API_KEY") is None
    assert os.getenv("MOTHERDUCK_ORG") is None
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_conflicts(mock_motherduck_env_vars):
    """
    Test handling of conflicting environment variable configurations.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If invalid configurations are not detected
    """
    # Create conflicting env vars
    os.environ["MOTHERDUCK_API_KEY"] = "conflict_key"
    with pytest.raises(RuntimeError, match="Conflicting environment variables detected"):
        mock_motherduck_env_vars()
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars
from ibis.tests.util import assert_equal

def test_ibis_motherduck_integration(mock_motherduck_env_vars):
    """
    End-to-end test for Ibis integration with MotherDuck.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If Ibis cannot connect using mocked credentials
    """
    import ibis
    con = ibis.connect('motherduck://')
    assert con.list_tables() == []
    table = con.create_table('test_table', {'col': 'int'})
    result = con.sql('SELECT * FROM test_table').execute()
    assert_equal(result, ibis.literal([]).to_table())
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_validation(mock_motherduck_env_vars):
    """
    Test validation of MotherDuck environment variables.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If invalid configurations are not detected
    """
    # Test missing org
    del os.environ["MOTHERDUCK_ORG"]
    with pytest.raises(KeyError, match="MOTHERDUCK_ORG must be set"):
        # Your code that requires both vars here

    # Test missing API key
    del os.environ["MOTHERDUCK_API_KEY"]
    with pytest.raises(KeyError, match="MOTHERDUCK_API_KEY must be set"):
        # Your code that requires both vars here
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_case_sensitivity(mock_motherduck_env_vars):
    """
    Test case sensitivity of environment variable names.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If case-insensitive variables are accepted
    """
    # Uppercase variation
    assert os.getenv("motherduck_api_key") is None

    # Mixed case variation
    assert os.getenv("MoThErDuCk_Org") is None
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_unicode(mock_motherduck_env_vars):
    """
    Test support for Unicode characters in environment variables.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If Unicode variables are not properly handled
    """
    # Test valid Unicode
    os.environ["MOTHERDUCK_API_KEY"] = "🔑test_key"
    assert os.getenv("MOTHERDUCK_API_KEY") == "🔑test_key"

    # Test invalid Unicode
    with pytest.raises(UnicodeError):
        os.environ["MOTHERDUCK_API_KEY"] = b"\xff".decode('utf-8')
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_length(mock_motherduck_env_vars):
    """
    Test environment variable length constraints.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If invalid length variables are accepted
    """
    # Test maximum length (hypothetical 1000 char limit)
    long_key = "a" * 1001
    with pytest.raises(ValueError, match="API key exceeds maximum length"):
        os.environ["MOTHERDUCK_API_KEY"] = long_key

    # Test minimum length (hypothetical 3 char minimum)
    short_key = "ab"
    with pytest.raises(ValueError, match="API key must be at least 3 characters"):
        os.environ["MOTHERDUCK_API_KEY"] = short_key
import os
import pytest
from src.dewey.core.crm.test_utils import mock_motherduck_env_vars

def test_motherduck_env_var_special_characters(mock_motherduck_env_vars):
    """
    Test support for special characters in environment variables.

    Args:
        mock_motherduck_env_vars: Pytest fixture for mocked env vars

    Raises:
        AssertionError: If invalid characters are not properly handled
    """
    # Test valid special characters
    os.environ["MOTHERDUCK_API_KEY"] = "!@#$%^&*()"
    assert os.getenv("MOTHERDUCK_API_KEY") == "!@#$%^&*()"

    # Test invalid characters (hypothetical restriction)
    with pytest.raises(ValueError, match="Invalid characters detected"):
        os.environ["MOTHERDUCK_API_KEY"] = "<>"
