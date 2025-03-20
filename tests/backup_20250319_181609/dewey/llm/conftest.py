import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def caplog_buffer(caplog):
    """Capture log messages in a buffer for easy assertion."""
    class BufferHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.buffer = []
        def emit(self, record):
            self.buffer.append(self.format(record))
    handler = BufferHandler()
    caplog.handler = handler
    logging.getLogger().addHandler(handler)
    yield handler.buffer
    logging.getLogger().removeHandler(handler)

@pytest.fixture
def mock_subprocess(mocker):
    """Fixture to mock asyncio subprocess calls."""
    mock_process = MagicMock()
    mock_process.wait = AsyncMock()
    mocker.patch("asyncio.create_subprocess_exec", return_value=mock_process)
    return mock_process
