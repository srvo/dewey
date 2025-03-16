"""PRD management system with architectural awareness and LLM integration."""

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ..llm.llm_utils import LLMHandler
from ..utils.vector_db import VectorStore
from .code_consolidator import CodeConsolidator, ConsolidationReporter


class PRDManager:
    """Interactive PRD builder with architectural guardrails."""

    def __init__(self, root_dir: Path = Path()) -> None:
        self.root_dir = root_dir
        self.console = Console()
        self.config = self._load_prd_config()
        self.prd_path = self._validate_prd_path()
        self.llm = LLMHandler(config={})  # Load from config in real implementation
        self.vector_db = VectorStore(collection_name="prd_components")
        self.conventions = self._load_conventions()
        self.prd_data = self._load_prd_template()
        self.reporter = ConsolidationReporter()
        self.code_insights = CodeConsolidator().analyze_directory()

    def _load_prd_config(self) -> dict:
        """Load PRD config from central dewey.yaml."""
        from dewey.config import load_config

        full_config = load_config()
        prd_config = full_config.get("prd", {})

        # Set defaults if section missing
        defaults = {
            "base_path": "config/prd",
            "active_prd": "current_prd.yaml",
            "schema": {
                "components": [
                    {"name": "", "purpose": "", "dependencies": [], "interfaces": []},
                ],
                "decisions": [
                    {
                        "timestamp": "datetime",
                        "description": "",
                        "alternatives": [],
                        "rationale": "",
                    },
                ],
            },
            "references": {
                "conventions": "../.aider/CONVENTIONS.md",
                "codebase_analysis": "../docs/codebase_analysis.md",
            },
        }

        return {**defaults, **prd_config}  # Merge with defaults

    def _validate_prd_path(self) -> Path:
        prd_dir = self.root_dir / self.config["prd"]["base_path"]
        prd_dir.mkdir(exist_ok=True, parents=True)
        return prd_dir / self.config["prd"]["active_prd"]

    def _load_conventions(self) -> dict:
        """Parse actual CONVENTIONS.md content."""
        conv_path = self.root_dir / self.config["prd"]["conventions_ref"]
        return self._parse_markdown_conventions(conv_path)

    def _parse_markdown_conventions(self, path: Path) -> dict:
        """Convert CONVENTIONS.md to structured data."""
        sections = {}
        current_section = None
        for line in path.read_text().splitlines():
            if line.startswith("# "):
                current_section = line[2:].lower().replace(" ", "_")
                sections[current_section] = []
            elif line.startswith("## "):
                subsect = line[3:].lower().replace(" ", "_")
                sections.setdefault(current_section, {})[subsect] = []
            elif current_section and line.strip():
                sections[current_section].append(line.strip())
        return sections

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

    def _find_consolidated_functions(self) -> list[Path]:
        """Discover consolidated function files."""
        consolidated_dir = self.root_dir / "consolidated_functions"
        return list(consolidated_dir.glob("consolidated_*.py"))

    def _analyze_consolidated_function(self, path: Path) -> dict:
        """Extract key details from a consolidated function file."""
        content = path.read_text()
        return {
            "path": path,
            "name": path.stem.replace("consolidated_", ""),
            "content": content,
            "dependencies": self._find_dependencies(content),
            "function_type": self._classify_function(content),
        }

    def _classify_function(self, code: str) -> str:
        """Use LLM to classify function purpose."""
        prompt = f"""Classify this Python function's purpose:
        {code}
        
        Output JSON with:
        - primary_category: "crm", "research", "accounting", "llm", "utils", "pipeline"
        - secondary_category: specific module if applicable
        - functionality_summary: 1-2 sentence description
        """
        response = self.llm.generate_response(prompt, response_format={"type": "json_object"})
        return json.loads(response)

    def _validate_location(self, proposed_path: Path) -> bool:
        """Ensure path matches project conventions."""
        parts = proposed_path.parts
        if "llm" in parts and "api_clients" not in parts:
            msg = "LLM components must be in llm/api_clients/ per CONVENTIONS.md"
            raise typer.BadParameter(
                msg,
            )
        return True

    def _architectural_review(self, func_desc: str) -> dict:
        """Enhanced LLM analysis with codebase context."""
        prompt = f"""
        Project Conventions:
        {json.dumps(self.conventions, indent=2)}

        Existing Components:
        {json.dumps(self._get_similar_components(func_desc), indent=2)}

        New Function Description: {func_desc}

        Output JSON with:
        - recommended_module: string (match project structure)
        - required_dependencies: list of existing components
        - architecture_rules: list of applicable conventions
        - potential_conflicts: list of strings
        """

        response = self.llm.generate_response(
            prompt,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response)

    def _get_similar_components(self, query: str) -> list:
        """Find related components using vector DB."""
        if not self.vector_db:
            return []

        return self.vector_db.collection.query(
            query_texts=[query],
            n_results=5,
            include=["metadatas"],
        )["metadatas"][0]

    def process_consolidated_functions(self) -> None:
        """Process all consolidated functions interactively."""
        self.console.print("[bold]Consolidated Function Relocation[/]")
        consolidated_files = self._find_consolidated_functions()
        
        for func_file in consolidated_files:
            analysis = self._analyze_consolidated_function(func_file)
            self._handle_single_function(analysis)

    def _handle_single_function(self, analysis: dict) -> None:
        """Handle relocation and documentation for a single function."""
        func_info = self._classify_function(analysis["content"])
        target_dir = self._determine_target_directory(func_info)
        
        self.console.print(f"\n[bold]Processing {analysis['name']}[/]")
        self.console.print(f"LLM Suggestion: {func_info['primary_category']} > {func_info['secondary_category']}")
        
        # Let user confirm or override
        choice = self.console.input(
            "Accept suggestion? (Y/n) \n"
            "Or choose module: [1]core [2]llm [3]utils [4]pipeline [5]skip "
        ).strip().lower()
        
        if choice in ["1", "2", "3", "4"]:
            target_dir = {
                "1": "core",
                "2": "llm",
                "3": "utils",
                "4": "pipeline"
            }[choice]
        elif choice == "5":
            return

        self._move_function_file(analysis["path"], target_dir, func_info)
        self._update_module_prd(target_dir, analysis, func_info)
        self._remove_duplicate_code(analysis)

    def _reformat_code(self, content: str, target_module: str) -> str:
        """Reformat code using LLM with Gemini first, DeepInfra fallback."""
        prompt = f"""Reformat this Python code to match our project conventions:
        - Add type hints
        - Include Google-style docstrings
        - Apply PEP 8 formatting
        - Add proper error handling
        - Remove unused imports
        - Make it match {target_module} module conventions
        
        Return only the reformed code with no commentary.
        
        Code to reformat:
        {content}
        """
        
        try:
            return self.llm.generate_response(
                prompt,
                model="gemini-2.0-flash",
                temperature=0.1,
                fallback_model="google/gemini-2.0-flash-001",
                max_tokens=4000
            )
        except Exception as e:
            self.console.print(f"[yellow]⚠️ Reformating failed: {e}[/yellow]")
            return content  # Return original if reformat fails

    def _move_function_file(self, src: Path, target_module: str, func_info: dict) -> None:
        """Move and reformat file with LLM-powered cleanup."""
        target_dir = self.root_dir / "src" / "dewey" / target_module
        target_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        existing_files = [f.name for f in target_dir.glob("*.py")]
        new_name = self._get_unique_filename(func_info["name"], existing_files)
        
        # Read, reformat, and write
        original_content = src.read_text()
        reformed_content = self._reformat_code(original_content, target_module)
        
        dest_path = target_dir / new_name
        dest_path.write_text(reformed_content)
        src.unlink()  # Remove original consolidated file
        
        self.console.print(f"✅ Moved to: [bold green]{dest_path.relative_to(self.root_dir)}[/]")
        self.console.print(f"📏 Size change: {len(original_content)} → {len(reformed_content)} chars")

    def _update_module_prd(self, module: str, analysis: dict, func_info: dict) -> None:
        """Create/update the module's PRD file."""
        prd_path = self.root_dir / "docs" / "prds" / f"{module}_prd.md"
        prd_path.parent.mkdir(exist_ok=True)
        
        content = f"\n## {func_info['name']}\n{func_info['functionality_summary']}\n"
        content += f"```python\n{analysis['content'][:500]}...\n```\n"
        
        if prd_path.exists():
            content = prd_path.read_text() + content
        prd_path.write_text(content)
        self.console.print(f"📄 Updated PRD: {prd_path.name}")

    def _remove_duplicate_code(self, analysis: dict) -> None:
        """Find and remove duplicate code implementations."""
        similar = self.vector_db.find_similar_functions(analysis["content"], threshold=0.95)
        if similar:
            self.console.print(f"Found {len(similar)} potential duplicates:")
            for path in similar:
                self.console.print(f" - {Path(path).relative_to(self.root_dir)}")
            
            if Confirm.ask("Delete duplicates?"):
                for path in similar:
                    Path(path).unlink()
                    self.console.print(f"🗑️ Deleted: {path}")

    def interactive_builder(self) -> None:
        """Guided PRD creation with validation."""
        self.console.print("[bold]PRD Builder[/]")

        while True:
            try:
                func_name = Prompt.ask("Function name (or 'exit')").strip()
                if func_name.lower() == "exit":
                    break

                if any(c in func_name for c in " _"):
                    self.console.print("[red]Use camelCase naming[/]", style="red")
                    continue

                func_desc = Prompt.ask("Description (include input/output types)")
                analysis = self._architectural_review(func_desc)

                self._display_analysis(analysis)

                if analysis.get("potential_conflicts"):
                    self.console.print("\n[bold]Conflicts Detected:[/]")
                    for conflict in analysis["potential_conflicts"]:
                        self.console.print(f"  ⚠️  {conflict}")

                if not Confirm.ask("Continue with this design?"):
                    continue

                self._record_component(func_name, func_desc, analysis)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Partial PRD saved[/]")
                break

        self._save_prd()
        self._generate_docs()

    def _save_prd(self) -> None:
        """Persist PRD data to YAML."""
        with open(self.prd_path, "w") as f:
            yaml.dump(self.prd_data, f, sort_keys=False)

    def _generate_docs(self) -> None:
        """Create Markdown version of PRD."""
        md_path = self.prd_path.with_suffix(".md")
        template = f"""
        # Project Requirements Document

        ## Components
        {self._format_components()}

        ## Architectural Decisions
        {self._format_decisions()}

        ## Convention Adherence
        {self._format_conventions()}
        """

        md_path.write_text(template)
        self.console.print(f"[green]Markdown PRD generated: {md_path}[/]")


app = typer.Typer()
console = Console()


@app.command()
def init() -> None:
    """Initialize new PRD with project scan."""
    manager = PRDManager()
    manager.interactive_builder()


@app.command()
def validate() -> None:
    """Check PRD against current codebase."""
    manager = PRDManager()
    report = manager.validate_prd()
    console.print(report)


@app.command()
def relocate() -> None:
    """Process consolidated functions and relocate them."""
    manager = PRDManager()
    manager.process_consolidated_functions()

@app.command()
def export() -> None:
    """Generate Markdown version."""
    manager = PRDManager()
    manager._generate_docs()


if __name__ == "__main__":
    app()
