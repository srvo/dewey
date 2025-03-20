import asyncio
import logging
import pytest
import shutil
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from dewey.llm.tool_launcher import ToolLauncher

@pytest.fixture
def tool_launcher():
    return ToolLauncher()

@pytest.fixture
def mock_subprocess(mocker):
    mock_process = MagicMock()
    mock_process.wait = AsyncMock()
    mock_create_subprocess_exec = mocker.patch(
        "asyncio.create_subprocess_exec",
        return_value=mock_process
    )
    return mock_create_subprocess_exec

class TestToolLauncher:

    async def test_tool_launcher_verify_tools_missing_tool(
        self, tool_launcher, caplog
    ):
        """Test that missing tools log a warning."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(shutil, "which", lambda x: None)
            tool_launcher._verify_tools()
            assert "Missing tools: visidata, gtop, wtfutil, frogmouth, calcure, harlequin" in caplog.text

    async def test_launch_tool_unknown_tool(self, tool_launcher):
        """Test launching unknown tool raises ValueError."""
        with pytest.raises(ValueError, match="Unknown tool: invalidtool"):
            await tool_launcher.launch_tool("invalidtool")

    async def test_launch_tool_missing_command(
        self, tool_launcher, mock_subprocess
    ):
        """Test launching tool with missing command raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Tool 'visidata' not found"):
            await tool_launcher.launch_tool("visidata")

    async def test_launch_tool_process_tracking(
        self, tool_launcher, mock_subprocess
    ):
        """Test process is tracked after launch."""
        await tool_launcher.launch_tool("gtop")
        assert "gtop" in tool_launcher.processes

    async def test_is_running(self, tool_launcher, mock_subprocess):
        """Test is_running reflects process state."""
        await tool_launcher.launch_tool("calcure")
        assert tool_launcher.is_running("calcure") is True

    async def test_stop_tool(self, tool_launcher, mock_subprocess):
        """Test stopping a tool removes it from processes."""
        await tool_launcher.launch_tool("harlequin")
        await tool_launcher.stop_tool("harlequin")
        assert "harlequin" not in tool_launcher.processes

    async def test_stop_all(self, tool_launcher, mock_subprocess):
        """Test stopping all tools clears processes."""
        await tool_launcher.launch_tool("visidata")
        await tool_launcher.launch_tool("frogmouth")
        await tool_launcher.stop_all()
        assert len(tool_launcher.processes) == 0

    async def test_monitor_process_logs_errors(
        self, tool_launcher, mock_subprocess
    ):
        """Test monitor logs errors from subprocess."""
        process = MagicMock()
        process.returncode = 1
        process.stderr = b"error message"
        await tool_launcher._monitor_process("test_tool", process)
        assert "test_tool stderr: error message" in tool_launcher.logger.handlers[0].buffer
        assert "test_tool exited with code 1" in tool_launcher.logger.handlers[0].buffer

@pytest.mark.parametrize("tool,args,expected_cmd", [
    ("visidata", "/tmp/data.csv", ["vd", "/tmp/data.csv"]),
    ("wtfutil", "--config /tmp/wtf.cfg", ["wtf", "--config", "/tmp/wtf.cfg"]),
])
async def test_launch_specific_tools(
    tool_launcher, mock_subprocess, tool, args, expected_cmd
):
    """Test specific tool launchers build correct commands."""
    await getattr(tool_launcher, f"launch_{tool.replace('util','')}")(args)
    mock_subprocess.assert_called_with(*expected_cmd, stdout=..., stderr=...)

async def test_async_context_manager(tool_launcher):
    """Test context manager stops all tools on exit."""
    async with tool_launcher as tl:
        await tl.launch_tool("gtop")
    assert len(tool_launcher.processes) == 0
