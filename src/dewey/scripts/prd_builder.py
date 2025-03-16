"""PRD management system with architectural awareness and LLM integration."""

from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ..llm.llm_utils import LLMHandler
from ..utils.vector_db import VectorStore
from .code_consolidator import ConsolidationReporter


class PRDManager:
    """Interactive PRD builder with architectural guardrails."""

    def __init__(self, root_dir: Path = Path()) -> None:
        self.console = Console()
        self.llm = LLMHandler(config={})  # Load from config in real implementation
        self.vector_db = VectorStore()
        self.conventions = self._load_conventions()
        self.prd_path = root_dir / "config/prd/current_prd.yaml"
        self.prd_data = self._load_prd_template()
        self.reporter = ConsolidationReporter()

    def _load_conventions(self) -> dict[str, Any]:
        """Parse CONVENTIONS.md into structured data."""
        # Implementation stub - would use regex to extract:
        return {
            "folder_structure": {
                "core": ["crm", "research", "accounting"],
                "llm": ["api_clients", "prompts"],
            },
            "arch_rules": ["No raw SQL", "Central LLM handler"],
        }

    def _load_prd_template(self) -> dict[str, Any]:
        """Load or initialize PRD structure."""
        if self.prd_path.exists():
            with open(self.prd_path) as f:
                return yaml.safe_load(f)
        return {
            "functions": [],
            "decisions": [],
            "components": [],
        }

    def _validate_location(self, proposed_path: Path) -> bool:
        """Ensure path matches project conventions."""
        parts = proposed_path.parts
        if "llm" in parts and "api_clients" not in parts:
            msg = "LLM components must be in llm/api_clients/ per CONVENTIONS.md"
            raise typer.BadParameter(
                msg,
            )
        return True

    def _architectural_review(self, func_desc: str) -> dict[str, str]:
        """LLM-powered architectural analysis."""
        prompt = f"""Based on our conventions: {self.conventions}
        Where should this function go? {func_desc}"""

        response = self.llm.generate_response(prompt)
        return {
            "module": "core/research",  # Example LLM response parsing
            "rationale": response,
        }

    def interactive_builder(self) -> None:
        """Guided PRD creation workflow."""
        self.console.print(
            "[bold]PRD Builder[/] - Let's define a production-ready function"
        )

        while True:
            func_name = Prompt.ask("Function name (or 'exit')")
            if func_name.lower() == "exit":
                break

            func_desc = Prompt.ask("Describe the function's purpose")
            analysis = self._architectural_review(func_desc)

            self.console.print(f"Suggested module: [green]{analysis['module']}[/]")
            confirm = Confirm.ask("Accept this placement?")

            if confirm:
                self.prd_data["functions"].append(
                    {
                        "name": func_name,
                        "purpose": func_desc,
                        "target_module": analysis["module"],
                        "status": "proposed",
                    }
                )

        self._save_prd()

    def _save_prd(self) -> None:
        """Persist PRD data to YAML."""
        with open(self.prd_path, "w") as f:
            yaml.dump(self.prd_data, f, sort_keys=False)


app = typer.Typer()
console = Console()


@app.command()
def init() -> None:
    """Initialize new PRD."""
    manager = PRDManager()
    manager.interactive_builder()
    console.print(f"[green]PRD created at {manager.prd_path}")


if __name__ == "__main__":
    app()
