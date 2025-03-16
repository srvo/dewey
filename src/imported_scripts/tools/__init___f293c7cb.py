"""Tools package for external tool integration."""

from __future__ import annotations

from .launcher import ToolLauncher

__all__ = ["ToolLauncher"]


def create_launcher() -> ToolLauncher:
    """Creates a ToolLauncher instance.

    Returns
    -------
        ToolLauncher: A new ToolLauncher instance.

    """
    return ToolLauncher()


def get_launcher_class() -> type[ToolLauncher]:
    """Returns the ToolLauncher class.

    Returns
    -------
        type[ToolLauncher]: The ToolLauncher class.

    """
    return ToolLauncher
