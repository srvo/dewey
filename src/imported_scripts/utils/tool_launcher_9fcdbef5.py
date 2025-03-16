"""Tool launcher for integrating external CLI tools."""

from __future__ import annotations

import asyncio
import logging
import shutil

from typing_extensions import Self

logger = logging.getLogger(__name__)


class ToolLauncher:
    """Launch and manage external CLI tools."""

    TOOL_COMMANDS: dict[str, str] = {
        "visidata": "vd",
        "gtop": "gtop",
        "wtfutil": "wtf",
        "frogmouth": "frogmouth",
        "calcure": "calcure",
        "harlequin": "harlequin",
    }

    def __init__(self) -> None:
        """Initialize the tool launcher."""
        self._verify_tools()
        self.processes: dict[str, asyncio.subprocess.Process] = {}

    def _verify_tools(self) -> None:
        """Verify that required tools are installed."""
        missing_tools: list[str] = []
        for tool, command in self.TOOL_COMMANDS.items():
            if not shutil.which(command):
                missing_tools.append(tool)

        if missing_tools:
            logger.warning(
                f"Missing tools: {', '.join(missing_tools)}. "
                "Install them using pip or your package manager.",
            )

    async def launch_tool(
        self,
        tool_name: str,
        args: list[str] | None = None,
    ) -> None:
        """Launch an external tool.

        Args:
        ----
            tool_name: Name of the tool to launch.
            args: Optional arguments to pass to the tool.

        Raises:
        ------
            ValueError: If the tool name is unknown.
            RuntimeError: If the tool is not found.

        """
        if tool_name not in self.TOOL_COMMANDS:
            msg = f"Unknown tool: {tool_name}"
            raise ValueError(msg)

        command = self.TOOL_COMMANDS[tool_name]
        if not shutil.which(command):
            msg = f"Tool '{tool_name}' not found. Please install it first."
            raise RuntimeError(
                msg,
            )

        cmd = [command] + (args or [])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self.processes[tool_name] = process
            asyncio.create_task(self._monitor_process(tool_name, process))

        except Exception as e:
            logger.exception(f"Error launching {tool_name}: {e!s}")
            raise

    async def _monitor_process(
        self,
        tool_name: str,
        process: asyncio.subprocess.Process,
    ) -> None:
        """Monitor a running process.

        Args:
        ----
            tool_name: Name of the tool being monitored.
            process: The asyncio process object.

        """
        try:
            stdout, stderr = await process.communicate()

            if stderr:
                logger.warning(f"{tool_name} stderr: {stderr.decode()}")

            if process.returncode != 0:
                logger.error(f"{tool_name} exited with code {process.returncode}")

            self.processes.pop(tool_name, None)

        except Exception as e:
            logger.exception(f"Error monitoring {tool_name}: {e!s}")

    def is_running(self, tool_name: str) -> bool:
        """Check if a tool is currently running.

        Args:
        ----
            tool_name: Name of the tool to check.

        Returns:
        -------
            True if the tool is running, False otherwise.

        """
        return tool_name in self.processes

    async def stop_tool(self, tool_name: str) -> None:
        """Stop a running tool.

        Args:
        ----
            tool_name: Name of the tool to stop.

        """
        if tool_name in self.processes:
            process = self.processes[tool_name]
            try:
                process.terminate()
                await process.wait()
            except Exception as e:
                logger.exception(f"Error stopping {tool_name}: {e!s}")
            finally:
                self.processes.pop(tool_name, None)

    async def stop_all(self) -> None:
        """Stop all running tools."""
        for tool_name in list(self.processes.keys()):
            await self.stop_tool(tool_name)

    async def launch_visidata(self, file_path: str | None = None) -> None:
        """Launch VisiData, optionally with a file.

        Args:
        ----
            file_path: Optional path to a file to open with VisiData.

        """
        args = [file_path] if file_path else None
        await self.launch_tool("visidata", args)

    async def launch_gtop(self) -> None:
        """Launch gtop system monitor."""
        await self.launch_tool("gtop")

    async def launch_wtf(self, config: str | None = None) -> None:
        """Launch WTF terminal dashboard.

        Args:
        ----
            config: Optional path to a WTF configuration file.

        """
        args = ["--config", config] if config else None
        await self.launch_tool("wtfutil", args)

    async def launch_frogmouth(self, file_path: str | None = None) -> None:
        """Launch Frogmouth markdown viewer.

        Args:
        ----
            file_path: Optional path to a markdown file to open with Frogmouth.

        """
        args = [file_path] if file_path else None
        await self.launch_tool("frogmouth", args)

    async def launch_calcure(self) -> None:
        """Launch Calcure calendar."""
        await self.launch_tool("calcure")

    async def launch_harlequin(self, connection_string: str | None = None) -> None:
        """Launch Harlequin SQL client.

        Args:
        ----
            connection_string: Optional connection string for Harlequin.

        """
        args = [connection_string] if connection_string else None
        await self.launch_tool("harlequin", args)

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_all()
