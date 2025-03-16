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
from .code_consolidator import CodeConsolidator, ConsolidationReporter


class PRDManager:
    """Interactive PRD builder with architectural guardrails."""

    def __init__(self, root_dir: Path = PROJECT_ROOT) -> None:
        self.root_dir = root_dir.resolve()
        self.console = Console()
        self.config = self._load_prd_config()
        self.prd_path = self._validate_prd_path()
        self.llm = LLMHandler(config={})  
        self.conventions = self._load_conventions()
        self.prd_data = self._load_prd_template()
        self.reporter = ConsolidationReporter()
        self.code_insights = self._analyze_codebase()
        self.modules = self._discover_modules()

    def _analyze_codebase(self) -> dict:
        """Recursively analyze codebase structure and content."""
        analyzer = CodeConsolidator()
        analyzer.root_path = self.root_dir
        return analyzer.analyze_directory()

    def _discover_modules(self) -> list[dict]:
        """Discover project modules with LLM-powered classification."""
        modules = []
        for path in self.root_dir.glob("src/dewey/**/*.py"):
            if path.name == "__init__.py" or not path.is_file():
                continue
            
            prompt = f"""Classify this Python module based on its path and content:
            Path: {path.relative_to(self.root_dir)}
            Content:
            {path.read_text()[:2000]}

            Output JSON with:
            - module_type: "core", "llm", "ui", "utils", "pipeline" 
            - purpose: 1-sentence description
            - key_functions: list of main functions/classes
            - dependencies: list of other modules it imports
            """
            
            try:
                analysis = json.loads(self.llm.generate_response(prompt, response_format={"type": "json_object"}))
                modules.append({
                    "path": str(path.relative_to(self.root_dir)),
                    **analysis
                })
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Error analyzing {path}: {e}[/yellow]")
        
        return modules

    def _load_prd_config(self) -> dict:
        """Load PRD config from central dewey.yaml."""
        # Get project root by going up 3 levels from llm directory
        project_root = self.root_dir.parent.parent.parent
        config_path = project_root / "config" / "dewey.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found at {config_path}. "
                f"Project root: {project_root}"
            )
        
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
        
        # Use project root from config loading
        project_root = self.root_dir.parent.parent.parent
        prd_dir = project_root / "config" / "prd"
        prd_dir.mkdir(exist_ok=True, parents=True)
        return prd_dir / active_prd

    def _load_conventions(self) -> dict:
        """Parse actual CONVENTIONS.md content."""
        # Use absolute path from project root per conventions
        conv_path = Path.home() / "dewey" / "CONVENTIONS.md"
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
        config_path = Path("/Users/srvo/dewey/config/dewey.yaml")
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
        from src.dewey.config import load_config

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
        """Find related components by module name."""
        return [m for m in self.modules if query.lower() in m.get("purpose", "").lower()]

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
        # Simple content-based duplicate detection
        similar = []
        for path in self.root_dir.glob("src/dewey/**/*.py"):
            if path.read_text() == analysis["content"] and path != analysis["path"]:
                similar.append(path)
                
        if similar:
            self.console.print(f"Found {len(similar)} exact duplicates:")
            for path in similar:
                self.console.print(f" - {path.relative_to(self.root_dir)}")

            if Confirm.ask("Delete duplicates?"):
                for path in similar:
                    path.unlink()
                    self.console.print(f"🗑️ Deleted: {path}")

    def interactive_builder(self) -> None:
        """Guided PRD creation with validation."""
        self.console.print("[bold cyan]PRD Builder[/bold cyan]\n")
        
        # Initialize with high-level requirements
        self._gather_overview()
        self._gather_components()
        self._gather_decisions()
        self._finalize_prd()
        
        self._save_prd()
        self._generate_docs()
        self.console.print("\n[bold green]✅ PRD generation complete![/bold green]")

    def _gather_overview(self) -> None:
        """Collect high-level PRD information."""
        self.console.print("[bold]Step 1/4: Project Overview[/bold]")
        
        # Use existing config or prompt for new values
        self.prd_data["title"] = Prompt.ask(
            "Project title", 
            default=self.prd_data.get("title", "Untitled Project")
        )
        
        self.prd_data["description"] = self.llm.generate_response(
            f"Generate a 1-paragraph project description based on these modules:\n"
            f"{json.dumps(self.modules, indent=2)}\n\n"
            "Keep it technical and concise."
        )
        
        self.console.print("\n[bold]Key Modules Found:[/bold]")
        for module in self.modules[:5]:  # Show top 5 most important
            self.console.print(f"  • {module['module_type']}: {module['purpose']}")

    def _gather_components(self) -> None:
        """Identify and document key components."""
        self.console.print("\n[bold]Step 2/4: Core Components[/bold]")
        
        for module in self.modules:
            if not Confirm.ask(f"\nDocument {module['module_type']} module '{Path(module['path']).name}'?"):
                continue
                
            # Generate component description using LLM
            prompt = f"""Describe this module for a technical PRD:
            Path: {module['path']}
            Key Functions: {', '.join(module['key_functions'])}
            Purpose: {module['purpose']}
            
            Output a 3-5 bullet point description focusing on architecture and business value.
            """
            description = self.llm.generate_response(prompt)
            
            self.prd_data.setdefault("components", []).append({
                "name": Path(module['path']).stem,
                "type": module['module_type'],
                "description": description,
                "dependencies": module['dependencies']
            })

    def _gather_decisions(self) -> None:
        """Document architectural decisions."""
        self.console.print("\n[bold]Step 3/4: Architectural Decisions[/bold]")
        
        while True:
            decision = {}
            decision["description"] = Prompt.ask(
                "\nDecision summary (or 'done' to finish)", 
                default="done"
            )
            
            if decision["description"].lower() == "done":
                break
                
            # Use LLM to flesh out decision details
            prompt = f"""Expand this architectural decision into structured PRD format:
            {decision['description']}
            
            Include:
            - Alternatives considered
            - Rationale
            - Impacted components
            - Tradeoffs
            """
            structured = self.llm.generate_response(prompt)
            decision.update(json.loads(structured))
            
            self.prd_data.setdefault("decisions", []).append(decision)
            self.console.print(f"\n[green]Added decision:[/green] {decision['description']}")

    def _finalize_prd(self) -> None:
        """LLM-assisted PRD polishing."""
        self.console.print("\n[bold]Step 4/4: Final Polish[/bold]")
        
        if Confirm.ask("Generate executive summary using LLM?"):
            prompt = f"""Write an executive summary for this PRD:
            {json.dumps(self.prd_data, indent=2)}
            
            Keep it under 3 paragraphs. Focus on technical architecture and business impact.
            """
            self.prd_data["executive_summary"] = self.llm.generate_response(prompt)
            
        if Confirm.ask("Validate PRD against coding conventions?"):
            issues = self._validate_conformance()
            if issues:
                self.console.print("\n[bold yellow]Convention Issues Found:[/bold yellow]")
                for issue in issues[:3]:  # Show top 3 issues
                    self.console.print(f"  • {issue}")
                    
            if Confirm.ask("Attempt automatic fixes with LLM?"):
                self._apply_convention_fixes()

    def _validate_conformance(self) -> list[str]:
        """Check PRD against project conventions."""
        prompt = f"""Review this PRD for convention compliance:
        PRD:
        {json.dumps(self.prd_data, indent=2)}
        
        Conventions:
        {json.dumps(self.conventions, indent=2)}
        
        List up to 5 non-compliance issues in bullet points.
        """
        return self.llm.generate_response(prompt).split("\n")

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
def init(target_dir: Path = typer.Argument(PROJECT_ROOT, help="Directory to analyze")) -> None:
    """Initialize new PRD with project scan.
    
    Args:
        target_dir: Directory path to analyze (defaults to project root)
    """
    manager = PRDManager(root_dir=target_dir)
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
