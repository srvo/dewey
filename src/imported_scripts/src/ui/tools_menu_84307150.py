"""Tools menu widget for launching external tools."""

import logging

from textual.binding import Binding
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from ..tools.launcher import ToolLauncher

logger = logging.getLogger(__name__)


class ToolsMenu(Tree):
    """Menu for launching external tools."""

    BINDINGS = [
        Binding("l", "launch", "Launch Tool", show=True),
        Binding("s", "stop", "Stop Tool", show=True),
        Binding("r", "refresh", "Refresh Status", show=True),
    ]

    def __init__(self) -> None:
        """Initialize the tools menu."""
        super().__init__(label="External Tools")
        self.launcher: ToolLauncher = ToolLauncher()

    def on_mount(self) -> None:
        """Set up the tools menu when mounted."""
        self.root.expand()
        self.populate_tools()

    def populate_tools(self) -> None:
        """Populate the menu with available tools."""
        self.root.remove_children()

        # Data Analysis
        data_node: TreeNode = self.root.add("Data Analysis", expand=True)
        data_node.add_leaf("VisiData - Data Explorer")
        data_node.add_leaf("Harlequin - SQL Client")

        # System Monitoring
        monitor_node: TreeNode = self.root.add("System Monitoring", expand=True)
        monitor_node.add_leaf("gtop - System Monitor")
        monitor_node.add_leaf("WTF - Terminal Dashboard")

        # Productivity
        productivity_node: TreeNode = self.root.add("Productivity", expand=True)
        productivity_node.add_leaf("Frogmouth - Markdown Viewer")
        productivity_node.add_leaf("Calcure - Calendar")

        self.refresh_status()

    def refresh_status(self) -> None:
        """Refresh the status indicators for running tools."""
        for node in self.walk_children(self.root):
            if isinstance(node, TreeNode):
                tool_name = self._get_tool_name(node.label)
                if tool_name:
                    running = self.launcher.is_running(tool_name)
                    node.label = f"{node.label} {'[Running]' if running else ''}"

    def _get_tool_name(self, label: str) -> str:
        """Extract tool name from label.

        Args:
            label: The label of the tool node.

        Returns:
            The tool name if found, otherwise an empty string.

        """
        if " - " not in label:
            return ""
        tool_name = label.split(" - ")[0].lower()
        return {
            "visidata": "visidata",
            "gtop": "gtop",
            "wtf": "wtfutil",
            "frogmouth": "frogmouth",
            "calcure": "calcure",
            "harlequin": "harlequin",
        }.get(tool_name, "")

    async def action_launch(self) -> None:
        """Launch the selected tool."""
        node = self.cursor_node
        if not node or not isinstance(node, TreeNode):
            return

        tool_name = self._get_tool_name(node.label)
        if not tool_name:
            return

        try:
            launch_method = getattr(self.launcher, f"launch_{tool_name}", None)
            if launch_method:
                await launch_method()
                self.refresh_status()

        except Exception as e:
            logger.exception(f"Error launching {tool_name}: {e!s}")

    async def action_stop(self) -> None:
        """Stop the selected tool."""
        node = self.cursor_node
        if not node or not isinstance(node, TreeNode):
            return

        tool_name = self._get_tool_name(node.label)
        if not tool_name:
            return

        try:
            await self.launcher.stop_tool(tool_name)
            self.refresh_status()

        except Exception as e:
            logger.exception(f"Error stopping {tool_name}: {e!s}")

    def action_refresh(self) -> None:
        """Refresh the tool status display."""
        self.refresh_status()

    async def on_unmount(self) -> None:
        """Clean up when widget is unmounted."""
        await self.launcher.stop_all()
