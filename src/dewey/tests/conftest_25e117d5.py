import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command line options to pytest."""
    parser.addoption(
        "--remote-host",
        action="store",
        default="test@localhost",
        help="Remote host to connect to",
    )
    parser.addoption(
        "--workspace",
        action="store",
        default="/tmp/test_workspace",
        help="Path to workspace directory",
    )


@pytest.fixture
def default_remote_host(request: pytest.FixtureRequest) -> str:
    """Fixture to provide the remote host."""
    return request.config.getoption("--remote-host")


@pytest.fixture
def default_workspace(request: pytest.FixtureRequest) -> str:
    """Fixture to provide the workspace path."""
    return request.config.getoption("--workspace")


def _parametrize_if_needed(metafunc: pytest.Metafunc, param_name: str) -> None:
    """Parametrize a test if the parameter is in the fixturenames."""
    if param_name in metafunc.fixturenames:
        metafunc.parametrize(param_name, [metafunc.config.getoption(param_name)])


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize tests based on command line options."""
    _parametrize_if_needed(metafunc, "remote_host")
    _parametrize_if_needed(metafunc, "workspace")
