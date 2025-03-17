"""Dewey Script Catalog - Textual UI Application."""

import os
from pathlib import Path
from typing import Dict, List

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Tree, Static
from textual.widgets.tree import TreeNode

class ScriptInfo:
    """Information about a script or module."""
    
    def __init__(self, path: Path, name: str, type: str):
        self.path = path
        self.name = name
        self.type = type
        self.description = ""
        self.usage = ""
        
    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        return f"{self.name} ({self.type})"

class ScriptDetails(Static):
    """Widget to display script details."""
    
    def __init__(self) -> None:
        super().__init__("")
        self.script_info = None
    
    def update_info(self, script_info: ScriptInfo) -> None:
        """Update displayed script information."""
        self.script_info = script_info
        content = f"""# {script_info.name}
Type: {script_info.type}
Path: {script_info.path}

## Description
{script_info.description or "No description available."}

## Usage
{script_info.usage or "No usage information available."}
"""
        self.update(content)

class DeweyApp(App):
    """Main Dewey Script Catalog application."""
    
    CSS = """
    Tree {
        width: 30%;
        border: solid $primary;
        scrollbar-gutter: stable;
        padding: 1;
    }
    
    ScriptDetails {
        width: 70%;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }
    
    #main-container {
        height: 100%;
    }
    """
    
    TITLE = "Dewey Script Catalog"
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        ("escape", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.scripts: Dict[str, ScriptInfo] = {}
        self.script_tree = Tree("Scripts")
        self.details = ScriptDetails()
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="main-container"):
            with Horizontal():
                yield self.script_tree
                yield self.details
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle app startup."""
        self.scan_scripts()
    
    def scan_scripts(self) -> None:
        """Scan for available scripts and modules."""
        dewey_root = Path(__file__).parent.parent
        
        # Clear existing tree
        self.script_tree.clear()
        self.scripts.clear()
        
        # Add core modules
        core_node = self.script_tree.root.add("Core Modules")
        for item in (dewey_root / "core").glob("**/*.py"):
            if item.name.startswith("_"):
                continue
            script_info = ScriptInfo(item, item.stem, "Core Module")
            self.scripts[str(item)] = script_info
            core_node.add(script_info.display_name).data = script_info
        
        # Add utility scripts
        utils_node = self.script_tree.root.add("Utilities")
        for item in (dewey_root / "utils").glob("**/*.py"):
            if item.name.startswith("_"):
                continue
            script_info = ScriptInfo(item, item.stem, "Utility")
            self.scripts[str(item)] = script_info
            utils_node.add(script_info.display_name).data = script_info
        
        # Add management scripts
        scripts_node = self.script_tree.root.add("Management Scripts")
        for item in (dewey_root / "scripts").glob("**/*.py"):
            if item.name.startswith("_"):
                continue
            script_info = ScriptInfo(item, item.stem, "Script")
            self.scripts[str(item)] = script_info
            scripts_node.add(script_info.display_name).data = script_info
        
        # Expand root node
        self.script_tree.root.expand()
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle selection of a script in the tree."""
        if event.node.data:
            self.details.update_info(event.node.data)
    
    def action_refresh(self) -> None:
        """Refresh the script catalog."""
        self.scan_scripts() 