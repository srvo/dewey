"""Test SSH service."""

from unittest.mock import AsyncMock, patch

import pytest
from ecic.services.ssh import SSHError, SSHService


@pytest.mark.asyncio
async def test_connect() -> None:
    """Test SSH connection."""
    mock_connection = AsyncMock()
    mock_connection.connect = AsyncMock()

    with patch("asyncssh.connect", return_value=mock_connection):
        service = SSHService()
        await service.connect("localhost", "user", "password")

        assert service.connected
        assert service.connection == mock_connection


@pytest.mark.asyncio
async def test_connect_error() -> None:
    """Test SSH connection error."""
    with patch("asyncssh.connect", side_effect=Exception("Connection failed")):
        service = SSHService()

        with pytest.raises(SSHError) as exc_info:
            await service.connect("localhost", "user", "wrong_password")

        assert "Connection failed" in str(exc_info.value)
        assert not service.connected
        assert service.connection is None


@pytest.mark.asyncio
async def test_disconnect() -> None:
    """Test SSH disconnection."""
    mock_connection = AsyncMock()
    mock_connection.close = AsyncMock()

    with patch("asyncssh.connect", return_value=mock_connection):
        service = SSHService()
        await service.connect("localhost", "user", "password")
        await service.disconnect()

        assert not service.connected
        assert service.connection is None
        mock_connection.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_command() -> None:
    """Test command execution."""
    mock_process = AsyncMock()
    mock_process.stdout = "command output"
    mock_process.stderr = ""
    mock_process.exit_status = 0

    mock_connection = AsyncMock()
    mock_connection.run = AsyncMock(return_value=mock_process)

    with patch("asyncssh.connect", return_value=mock_connection):
        service = SSHService()
        await service.connect("localhost", "user", "password")

        result = await service.execute("ls -l")
        assert result.stdout == "command output"
        assert result.stderr == ""
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_command_error() -> None:
    """Test command execution error."""
    mock_process = AsyncMock()
    mock_process.stdout = ""
    mock_process.stderr = "command failed"
    mock_process.exit_status = 1

    mock_connection = AsyncMock()
    mock_connection.run = AsyncMock(return_value=mock_process)

    with patch("asyncssh.connect", return_value=mock_connection):
        service = SSHService()
        await service.connect("localhost", "user", "password")

        result = await service.execute("invalid_command")
        assert result.stderr == "command failed"
        assert result.exit_code == 1


@pytest.mark.asyncio
async def test_execute_without_connection() -> None:
    """Test executing command without connection."""
    service = SSHService()

    with pytest.raises(SSHError) as exc_info:
        await service.execute("ls -l")
    assert "Not connected" in str(exc_info.value)
