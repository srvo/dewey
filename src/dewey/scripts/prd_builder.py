"""PRD management system with architectural awareness and LLM integration."""

# Added early path configuration before any imports
import sys
import pathlib
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

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

    def __init__(self, root_dir: Path = PROJECT_ROOT) -> None:
        self.root_dir = root_dir.resolve()
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
        config_path = self.root_dir / "config/dewey.yaml"
        
        try:
            with open(config_path) as f:
                full_config = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            self.console.print(f"[yellow]⚠️ Config loading failed: {e} - Using defaults[/yellow]")
            full_config = {}

        prd_config = full_config.get("prd", {})
        
        return {
            "base_path": prd_config.get("base_path", "config/prd"),
            "active_prd": prd_config.get("active_prd", "current_prd.yaml"),
            "schema": prd_config.get("schema", {
                "components": [{"name": "", "purpose": "", "dependencies": [], "interfaces": []}],
                "decisions": [{"timestamp": "datetime", "description": "", "alternatives": [], "rationale": ""}]
            }),
            "references": prd_config.get("references", {
                "conventions": "../.aider/CONVENTIONS.md",
                "codebase_analysis": "../docs/codebase_analysis.md"
            })
        }

    def _validate_prd_path(self) -> Path:
        # Get with safe defaults from direct config keys
        base_path = self.config.get("base_path", "config/prd")
        active_prd = self.config.get("active_prd", "current_prd.yaml")
        
        prd_dir = self.root_dir / base_path
        prd_dir.mkdir(exist_ok=True, parents=True)
        return prd_dir / active_prd

    def _load_conventions(self) -> dict:
        """Parse actual CONVENTIONS.md content."""
        conv_path = self.root_dir / self.config["references"]["conventions"]
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


    def _load_prd_template(self) -> dict[str, Any]:
        """Load PRD structure with base template and existing content."""
        config_path = self.root_dir / "config" / "dewey.yaml"
        base_template = {}
        
        try:
            with open(config_path) as f:
                base_template = yaml.safe_load(f).get("prd", {}).get("base_template", {})
        except (FileNotFoundError, yaml.YAMLError) as e:
            self.console.print(f"[yellow]⚠️ Template loading failed: {e} - Using empty template[/yellow]")

        if self.prd_path.exists():
            try:
                with open(self.prd_path) as f:
                    existing_content = yaml.safe_load(f)
                    return self._deep_merge(base_template, existing_content)
            except yaml.YAMLError as e:
                self.console.print(f"[red]Error loading existing PRD: {e}[/red]")

        return base_template

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Recursively merge two dictionaries."""
        for key, val in update.items():
            if isinstance(val, dict):
                base[key] = self._deep_merge(base.get(key, {}), val)
            elif key not in base:  # Only add new keys, don't overwrite
                base[key] = val
        return base

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
        response = self.llm.generate_response(
            prompt, response_format={"type": "json_object"}
        )
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
        """Enhanced LLM analysis with stakeholder context."""
        from dewey.config import load_config

        prd_config = load_config().get("prd", {})

        prompt = f"""
        Project Conventions:
        {json.dumps(self.conventions, indent=2)}

        Stakeholder Context:
        {json.dumps(prd_config.get('base_template', {}).get('stakeholders'), indent=2)}

        Existing Components:
        {json.dumps(self._get_similar_components(func_desc), indent=2)}

        New Function Description: {func_desc}

        Output JSON with:
        - recommended_module: string (match project structure)
        - required_dependencies: list of existing components
        - architecture_rules: list of applicable conventions
        - stakeholder_impact: list of affected stakeholders
        - security_considerations: list of strings
        - data_sources: list of required data inputs
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
        self.console.print(
            f"LLM Suggestion: {func_info['primary_category']} > {func_info['secondary_category']}"
        )

        # Let user confirm or override
        choice = (
            self.console.input(
                "Accept suggestion? (Y/n) \n"
                "Or choose module: [1]core [2]llm [3]utils [4]pipeline [5]skip ",
            )
            .strip()
            .lower()
        )

        if choice in ["1", "2", "3", "4"]:
            target_dir = {
                "1": "core",
                "2": "llm",
                "3": "utils",
                "4": "pipeline",
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
                max_tokens=4000,
            )
        except Exception as e:
            self.console.print(f"[yellow]⚠️ Reformating failed: {e}[/yellow]")
            return content  # Return original if reformat fails

    def _move_function_file(
        self, src: Path, target_module: str, func_info: dict
    ) -> None:
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

        self.console.print(
            f"✅ Moved to: [bold green]{dest_path.relative_to(self.root_dir)}[/]"
        )
        self.console.print(
            f"📏 Size change: {len(original_content)} → {len(reformed_content)} chars"
        )

    def _update_module_prd(self, module: str, analysis: dict, func_info: dict) -> None:
        """Update PRD with structured function documentation."""
        prd_path = self.root_dir / "docs" / "prds" / f"{module}_prd.md"
        prd_path.parent.mkdir(exist_ok=True)

        # Load existing or initialize with base structure
        prd_content = self._load_prd_template()

        # Add function-specific content to appropriate sections
        func_entry = {
            "name": func_info["name"],
            "summary": func_info["functionality_summary"],
            "category": func_info["primary_category"],
            "dependencies": analysis["dependencies"],
            "complexity": len(analysis["content"])
            // 100,  # Simple complexity heuristic
        }

        # Add to requirements section
        prd_content.setdefault("requirements", {}).setdefault("functional", []).append(
            func_entry
        )

        # Add technical spec
        tech_spec = {
            "function": func_info["name"],
            "input_types": self._detect_input_types(analysis["content"]),
            "output_type": self._detect_output_type(analysis["content"]),
            "error_handling": "Present" if "try" in analysis["content"] else "Basic",
        }
        prd_content.setdefault("technical_specs", []).append(tech_spec)

        # Save updated PRD
        with open(prd_path, "w") as f:
            yaml.dump(prd_content, f, sort_keys=False)

        self.console.print(f"📄 Updated structured PRD: {prd_path.name}")

    def _detect_input_types(self, code: str) -> list:
        """Simple type detection from function code."""
        types = []
        if "DataFrame" in code:
            types.append("pandas.DataFrame")
        if "ibis" in code:
            types.append("ibis.Table")
        if "def __init__" in code:
            types.append("ConfigDict")
        return types or ["Any"]

    def _detect_output_type(self, code: str) -> str:
        """Detect output type from code patterns."""
        if "return pd." in code:
            return "pandas.DataFrame"
        if "return ibis." in code:
            return "ibis.Table"
        if "return {" in code:
            return "dict"
        return "None"

    def _remove_duplicate_code(self, analysis: dict) -> None:
        """Find and remove duplicate code implementations."""
        similar = self.vector_db.find_similar_functions(
            analysis["content"], threshold=0.95
        )
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
