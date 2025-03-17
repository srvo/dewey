"""Repository architecture analyzer using PRDs and Gemini API.

This script loads PRDs from each repository, analyzes them using Gemini API,
and provides feedback on the overall architecture and suggested improvements.
"""

import os
import sys
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table

# Add parent directory to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dewey.llm.llm_utils import LLMHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Architecture Analyzer")

class ArchitectureAnalyzer:
    """Analyzes repository architecture using PRDs and Gemini API."""

    def __init__(self) -> None:
        """Initialize the analyzer."""
        self.console = Console()
        self.project_root = Path("/Users/srvo/dewey")  # Hardcoded for simplicity
        self.llm = self._init_llm()
        
    def _init_llm(self) -> LLMHandler:
        """Initialize the LLM handler with proper configuration."""
        config_path = self.project_root / "config" / "dewey.yaml"
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                
            # Get LLM config with defaults
            llm_config = config.get("llm", {})
            if not llm_config:
                logger.warning("No LLM configuration found in config file, using defaults")
                llm_config = {
                    "default_provider": "deepinfra",
                    "providers": {
                        "deepinfra": {
                            "default_model": "google/gemini-2.0-flash-001"
                        }
                    }
                }
                
            logger.info(f"Initializing LLM with config: {llm_config}")
            return LLMHandler(llm_config)
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise

    def find_prds(self) -> List[Path]:
        """Find all PRD files in the repository."""
        prds = []
        for path in self.project_root.rglob("*_Product_Requirements_Document.yaml"):
            if "docs" in path.parts and not path.name.startswith("."):
                prds.append(path)
        return prds

    def load_prd(self, prd_path: Path) -> Dict[str, Any]:
        """Load a PRD file."""
        try:
            with open(prd_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load PRD {prd_path}: {e}")
            return {}

    def analyze_architecture(self) -> None:
        """Analyze the overall repository architecture."""
        self.console.print("\n[bold cyan]🏗️  Repository Architecture Analysis[/bold cyan]\n")

        try:
            # Find and load all PRDs
            prds = self.find_prds()
            if not prds:
                self.console.print("[yellow]No PRDs found in repository[/yellow]")
                return

            self.console.print(f"Found {len(prds)} PRDs to analyze:")
            for prd in prds:
                self.console.print(f"  • {prd.relative_to(self.project_root)}")

            # Load all PRDs
            prd_data = {}
            for prd_path in prds:
                module_name = prd_path.stem.replace("_Product_Requirements_Document", "")
                prd_data[module_name] = self.load_prd(prd_path)

            # Analyze overall architecture
            self.console.print("\n[bold]Analyzing architecture...[/bold]")
            analysis = self._analyze_with_llm(prd_data)
            
            if not analysis:
                self.console.print("[red]Architecture analysis failed[/red]")
                return
                
            self._display_analysis(analysis)
            
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            self.console.print(f"[red]Error during architecture analysis: {e}[/red]")
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Detailed traceback:")

    def _analyze_with_llm(self, prd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the architecture using LLM API."""
        prompt = f"""Analyze this repository's architecture based on its PRDs:

Repository Structure:
{json.dumps(prd_data, indent=2)}

Provide a comprehensive JSON analysis with:
{{
    "overall_assessment": {{
        "architecture_style": "The primary architectural style/pattern used",
        "strengths": ["List of architectural strengths"],
        "weaknesses": ["List of architectural weaknesses"]
    }},
    "module_organization": {{
        "logical_grouping": "Assessment of how well modules are organized",
        "dependency_management": "Assessment of dependency relationships",
        "suggested_reorganization": ["List of suggested organizational changes"]
    }},
    "information_flow": {{
        "primary_flows": ["List of main information flows between modules"],
        "bottlenecks": ["List of potential bottlenecks"],
        "optimization_suggestions": ["List of suggested optimizations"]
    }},
    "maintainability": {{
        "current_assessment": "Assessment of current maintainability",
        "risk_factors": ["List of factors that could affect maintainability"],
        "improvement_suggestions": ["List of suggested improvements"]
    }},
    "proposed_changes": [
        {{
            "area": "Area of change",
            "current_state": "Description of current state",
            "proposed_change": "Description of proposed change",
            "benefits": ["List of benefits"],
            "implementation_complexity": "High/Medium/Low"
        }}
    ]
}}

Focus on:
1. Logical organization and future extensibility
2. Information flow and dependencies
3. Maintainability and technical debt
4. Concrete, actionable improvements"""

        try:
            # Use lower temperature for more consistent analysis
            response = self.llm.generate_response(
                prompt,
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
                strict_json=True
            )
            
            # Log the raw response for debugging
            logger.debug(f"Architecture analysis response: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to analyze architecture: {e}")
            # Return a safe fallback structure
            return {
                "overall_assessment": {
                    "architecture_style": "Unknown (analysis failed)",
                    "strengths": [],
                    "weaknesses": ["Analysis failed to complete"]
                },
                "module_organization": {
                    "logical_grouping": "Analysis incomplete",
                    "dependency_management": "Analysis incomplete",
                    "suggested_reorganization": []
                },
                "information_flow": {
                    "primary_flows": [],
                    "bottlenecks": [],
                    "optimization_suggestions": []
                },
                "maintainability": {
                    "current_assessment": "Analysis incomplete",
                    "risk_factors": ["Analysis failed to complete"],
                    "improvement_suggestions": []
                },
                "proposed_changes": []
            }

    def _display_analysis(self, analysis: Dict[str, Any]) -> None:
        """Display the architecture analysis in a structured format."""
        if not analysis:
            self.console.print("[red]Failed to generate architecture analysis[/red]")
            return

        # Overall Assessment
        self.console.print("\n[bold]Overall Architecture Assessment[/bold]")
        if "overall_assessment" in analysis:
            overall = analysis["overall_assessment"]
            self.console.print(f"\nArchitecture Style: {overall.get('architecture_style', 'Not specified')}")
            
            self.console.print("\n[green]Strengths:[/green]")
            for strength in overall.get("strengths", []):
                self.console.print(f"  • {strength}")
                
            self.console.print("\n[yellow]Weaknesses:[/yellow]")
            for weakness in overall.get("weaknesses", []):
                self.console.print(f"  • {weakness}")

        # Module Organization
        if "module_organization" in analysis:
            self.console.print("\n[bold]Module Organization[/bold]")
            org = analysis["module_organization"]
            self.console.print(f"\nLogical Grouping: {org.get('logical_grouping', 'Not specified')}")
            self.console.print(f"Dependency Management: {org.get('dependency_management', 'Not specified')}")
            
            self.console.print("\nSuggested Reorganization:")
            for suggestion in org.get("suggested_reorganization", []):
                self.console.print(f"  • {suggestion}")

        # Information Flow
        if "information_flow" in analysis:
            self.console.print("\n[bold]Information Flow Analysis[/bold]")
            flow = analysis["information_flow"]
            
            self.console.print("\nPrimary Flows:")
            for flow_path in flow.get("primary_flows", []):
                self.console.print(f"  • {flow_path}")
                
            self.console.print("\n[yellow]Bottlenecks:[/yellow]")
            for bottleneck in flow.get("bottlenecks", []):
                self.console.print(f"  • {bottleneck}")
                
            self.console.print("\nOptimization Suggestions:")
            for suggestion in flow.get("optimization_suggestions", []):
                self.console.print(f"  • {suggestion}")

        # Maintainability
        if "maintainability" in analysis:
            self.console.print("\n[bold]Maintainability Assessment[/bold]")
            maint = analysis["maintainability"]
            self.console.print(f"\nCurrent Assessment: {maint.get('current_assessment', 'Not specified')}")
            
            self.console.print("\n[yellow]Risk Factors:[/yellow]")
            for risk in maint.get("risk_factors", []):
                self.console.print(f"  • {risk}")
                
            self.console.print("\nImprovement Suggestions:")
            for suggestion in maint.get("improvement_suggestions", []):
                self.console.print(f"  • {suggestion}")

        # Proposed Changes
        if "proposed_changes" in analysis:
            self.console.print("\n[bold]Proposed Architectural Changes[/bold]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Area")
            table.add_column("Current State")
            table.add_column("Proposed Change")
            table.add_column("Complexity")
            
            for change in analysis["proposed_changes"]:
                table.add_row(
                    change.get("area", ""),
                    change.get("current_state", ""),
                    change.get("proposed_change", ""),
                    change.get("implementation_complexity", "")
                )
            
            self.console.print(table)

def main() -> None:
    """Run the architecture analysis."""
    analyzer = ArchitectureAnalyzer()
    analyzer.analyze_architecture()

if __name__ == "__main__":
    try:
        # Ensure we're in the project root
        if not os.path.exists("config/dewey.yaml"):
            msg = "Please run this script from the project root directory"
            raise RuntimeError(msg)
            
        main()
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Detailed traceback:")
        sys.exit(1) 