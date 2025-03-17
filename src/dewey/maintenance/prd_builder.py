"""PRD management system with architectural awareness and LLM integration."""

import json
import logging
import os
import pathlib
import random
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import typer
import yaml
from rich.console import Console
from rich.prompt import Confirm, Prompt
import ast
import argparse

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("PRD Builder")

# Add parent directory to sys.path to avoid import issues
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dewey.llm.llm_utils import LLMHandler

def load_config() -> dict:
    """Load configuration from dewey.yaml."""
    config_path = Path("/Users/srvo/dewey/config/dewey.yaml")
    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}")
        return {}
    
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

class PRDManager:
    """Interactive PRD builder with architectural guardrails."""

    def __init__(self, project_root: str, prd_path: str | None, llm: LLMHandler) -> None:
        """Initialize the PRD manager."""
        self.project_root = project_root
        self.llm = llm
        self.console = Console()
        self.prd_data = {}
        self.modules = {}
        
        # Set and validate PRD path
        if prd_path:
            self.prd_path = prd_path
        else:
            self.prd_path = self._validate_prd_path()
        
        # Initialize component tracking
        self.components = []
        self.component_descriptions = {}
        self.component_responsibilities = {}
        self.component_dependencies = {}
        
        # Initialize decision tracking
        self.critical_issues = []
        self.issue_impacts = {}
        self.issue_changes = {}
        self.issue_priorities = {}
        self.architecture_patterns = []
        
        # Load conventions
        self.conventions = self._load_conventions()

    def _analyze_repository(self) -> None:
        """Analyze the repository structure and identify key components."""
        try:
            # First gather actual file information with detailed analysis
            components = {}
            
            # Walk through the directory structure
            for root, dirs, files in os.walk(self.project_root):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.project_root)
                        
                        # Skip __init__.py and test files
                        if file == '__init__.py' or file.endswith('_test.py'):
                            continue
                            
                        # Analyze the file
                        component_info = self._analyze_component(file_path, rel_path)
                        if component_info:
                            components[rel_path] = component_info
                            # Add to components list for processing
                            self.components.append(rel_path)
                            
                            # Extract architecture patterns from component analysis
                            if 'patterns' in component_info:
                                self.architecture_patterns.extend(
                                    pattern for pattern in component_info['patterns']
                                    if pattern not in self.architecture_patterns
                                )

            # Initialize the components section if it doesn't exist
            if 'components' not in self.prd_data:
                self.prd_data['components'] = {}

            # Store discovered modules
            self.modules = self._discover_modules(self.project_root)
            
            # Process components to extract descriptions, responsibilities, and dependencies
            for rel_path, info in components.items():
                self.component_descriptions[rel_path] = info.get('description', '')
                self.component_responsibilities[rel_path] = info.get('responsibilities', [])
                self.component_dependencies[rel_path] = info.get('dependencies', [])
                
                # Extract critical issues
                if 'issues' in info:
                    for issue in info['issues']:
                        if issue not in self.critical_issues:
                            self.critical_issues.append(issue)
                            self.issue_impacts[issue] = info.get('issue_impacts', {}).get(issue, '')
                            self.issue_changes[issue] = info.get('issue_changes', {}).get(issue, '')
                            self.issue_priorities[issue] = info.get('issue_priorities', {}).get(issue, 'medium')

            self.console.print(f"\n✅ Successfully analyzed repository structure")
            
        except Exception as e:
            self.console.print(f"\n[bold red]❌ Error analyzing repository:[/bold red] {str(e)}")
            raise

    def _analyze_component(self, file_path: str, rel_path: str) -> dict:
        """Analyze a single component (file) and extract its details."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            component_info = {
                'description': 'No description available.',
                'responsibilities': [],
                'dependencies': [],
                'classes': [],
                'functions': [],
                'imports': []
            }
            
            # First try full AST parsing
            try:
                tree = ast.parse(content)
                component_info['description'] = ast.get_docstring(tree) or component_info['description']
                
                # Extract imports, classes and functions using AST
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            component_info['imports'].append(name.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        for name in node.names:
                            component_info['imports'].append(f"{module}.{name.name}")
                    elif isinstance(node, ast.ClassDef):
                        class_info = {
                            'name': node.name,
                            'docstring': ast.get_docstring(node) or 'No description available.',
                            'methods': []
                        }
                        for method in [n for n in node.body if isinstance(n, ast.FunctionDef)]:
                            method_info = {
                                'name': method.name,
                                'docstring': ast.get_docstring(method) or 'No description available.'
                            }
                            class_info['methods'].append(method_info)
                        component_info['classes'].append(class_info)
                    elif isinstance(node, ast.FunctionDef):
                        if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                            function_info = {
                                'name': node.name,
                                'docstring': ast.get_docstring(node) or 'No description available.'
                            }
                            component_info['functions'].append(function_info)
                            
            except SyntaxError:
                # Fallback to regex-based parsing for malformed files
                self.console.print(f"[yellow]Using fallback parsing for {rel_path}[/yellow]")
                
                # Try to extract imports using regex
                import re
                import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        match = re.match(import_pattern, line)
                        if match:
                            module, names = match.groups()
                            names = [n.strip() for n in names.split(',')]
                            for name in names:
                                if ' as ' in name:
                                    name = name.split(' as ')[0]
                                if module:
                                    component_info['imports'].append(f"{module}.{name}")
                                else:
                                    component_info['imports'].append(name)
                
                # Try to extract classes and functions using regex
                class_pattern = r'class\s+(\w+)[:\(]'
                func_pattern = r'def\s+(\w+)\s*\('
                
                for match in re.finditer(class_pattern, content):
                    class_info = {
                        'name': match.group(1),
                        'docstring': 'No description available (parsed from invalid syntax)',
                        'methods': []
                    }
                    component_info['classes'].append(class_info)
                    
                for match in re.finditer(func_pattern, content):
                    func_name = match.group(1)
                    # Skip if it looks like a method (indented)
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    if not content[line_start:match.start()].strip():
                        function_info = {
                            'name': func_name,
                            'docstring': 'No description available (parsed from invalid syntax)'
                        }
                        component_info['functions'].append(function_info)
                
                # Try to extract docstring using regex
                docstring_pattern = r'"""(.*?)"""'
                docstring_matches = re.finditer(docstring_pattern, content, re.DOTALL)
                first_docstring = next(docstring_matches, None)
                if first_docstring:
                    component_info['description'] = first_docstring.group(1).strip()
            
            # Generate responsibilities based on classes and functions
            component_info['responsibilities'] = self._generate_responsibilities(component_info)
            
            # Identify dependencies
            component_info['dependencies'] = self._identify_dependencies(component_info['imports'])
            
            return component_info
            
        except Exception as e:
            self.console.print(f"[yellow]Error analyzing {rel_path}: {e}[/yellow]")
            return None

    def _generate_responsibilities(self, component_info: dict) -> list:
        """Generate a list of responsibilities based on component analysis."""
        responsibilities = set()
        
        # Prepare all items for batch analysis
        items_to_analyze = []
        
        # Add classes with their methods
        for class_info in component_info['classes']:
            items_to_analyze.append({
                "type": "class",
                "name": class_info['name'],
                "docstring": class_info['docstring'],
                "methods": [
                    {"name": m["name"], "docstring": m["docstring"]} 
                    for m in class_info.get("methods", [])
                ]
            })
        
        # Add standalone functions
        for func_info in component_info['functions']:
            items_to_analyze.append({
                "type": "function",
                "name": func_info['name'],
                "docstring": func_info['docstring']
            })
        
        if not items_to_analyze:
            return list(responsibilities)
        
        # Create a single prompt for all items
        prompt = f"""Analyze these Python components and list their key responsibilities.
Return ONLY a JSON object with this structure, no other text:
{{
    "responsibilities": [
        {{
            "name": "component_name",
            "type": "class|function",
            "responsibilities": ["responsibility1", "responsibility2", ...]
        }}
    ]
}}

For each class, list up to 3 key responsibilities.
For each function, list its main responsibility.
Be concise and specific. Focus on what each component does, not how it does it.

Components to analyze:
{json.dumps(items_to_analyze, indent=2)}"""
        
        try:
            # Use LLMHandler with response format specified
            response = self.llm.generate_response(
                prompt,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Handle both string and dict responses
            if isinstance(response, str):
                try:
                    parsed_response = json.loads(response)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse response as JSON")
                    return list(responsibilities)
            else:
                parsed_response = response
            
            # Extract responsibilities from the parsed response
            if isinstance(parsed_response, dict) and "responsibilities" in parsed_response:
                for item in parsed_response["responsibilities"]:
                    if isinstance(item, dict) and "responsibilities" in item:
                        # Ensure we're only adding strings to the set
                        for resp in item["responsibilities"]:
                            if isinstance(resp, str):
                                responsibilities.add(resp)
            
        except Exception as e:
            logger.warning(f"Error generating responsibilities: {e}")
        
        return list(responsibilities)

    def _identify_dependencies(self, imports: list) -> list:
        """Convert import statements to meaningful dependencies."""
        dependencies = set()
        
        for imp in imports:
            # Handle internal dependencies
            if imp.startswith('dewey.'):
                parts = imp.split('.')
                if len(parts) >= 3:  # dewey.module.component
                    dependencies.add(f"{parts[2]}.py for {parts[1]} functionality")
            # Handle external dependencies
            elif not imp.startswith(('os', 'sys', 'typing', 'logging', 'json', 'yaml')):
                dependencies.add(f"{imp.split('.')[0]} library")
        
        return list(dependencies)

    def _group_components_by_directory(self, components: dict) -> dict:
        """Group components by directory and create a hierarchical structure."""
        grouped = {}
        
        for path, info in components.items():
            parts = path.split('/')
            
            # Handle root-level Python files
            if len(parts) == 1:
                grouped[parts[0]] = info
                continue
            
            # Handle files in directories
            current_level = grouped
            for i, part in enumerate(parts[:-1]):
                if part not in current_level:
                    current_level[part] = {
                        'description': f'Directory containing {part}-related components.',
                        'responsibilities': [],
                        'dependencies': [],
                        'subcomponents': {}
                    }
                
                # Special handling for known directories
                if part == 'agents':
                    current_level[part]['dependencies'].append('smolagents framework as the core agent infrastructure')
                elif part == 'api_clients':
                    current_level[part]['dependencies'].extend([
                        'google.generativeai for Gemini',
                        'openai for DeepInfra',
                        'exceptions.py for error handling'
                    ])
                
                current_level = current_level[part]['subcomponents']
            
            # Add the file as a component
            current_level[parts[-1]] = info
        
        return grouped

    def _find_python_files(self, directory: Path) -> Iterator[Path]:
        """Yield Python files in directory, ignoring hidden/log files."""
        for path in directory.rglob("*"):
            if path.suffix == ".py" and not path.name.startswith("__"):
                if "/logs/" not in str(path) and not path.name.endswith("_test.py"):
                    yield path

    def _refine_analysis(self, analysis_type: str, initial_response: str, context: dict) -> dict:
        """Refine the initial analysis with additional context."""
        try:
            # Parse initial response using LLMHandler
            initial_result = self.llm.parse_json_response(initial_response)
            
            # Prepare refinement prompt
            prompt = f"""Please refine the following {analysis_type} analysis with additional context.
            
Initial Analysis:
{json.dumps(initial_result, indent=2)}

Additional Context:
{json.dumps(context, indent=2)}

Please provide a refined analysis that:
1. Incorporates the additional context
2. Maintains the same JSON structure
3. Adds or updates fields based on the new information
4. Resolves any inconsistencies between the initial analysis and context"""

            # Get refined analysis with fallback support
            response = self.llm.generate_response(
                prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse refined response using LLMHandler
            refined = self.llm.parse_json_response(response)
            
            return refined
            
        except Exception as e:
            logger.error(f"Error refining analysis: {e}")
            return initial_result

    def _architectural_review(self, func_desc: str) -> dict:
        """Get architectural review of a function."""
        try:
            prompt = f"""Review this function for architectural fit:

            {func_desc}

            Provide a JSON response with:
            {{
                "module": "Recommended module path",
                "patterns": ["Architectural patterns used"],
                "concerns": ["Any architectural concerns"],
                "recommendations": ["Improvement suggestions"]
            }}"""

            # Add timeout and lower temperature for more reliable responses
            response = self.llm.generate_response(
                prompt,
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
                strict_json=True
            )
            
            # Log the raw response for debugging
            logger.debug(f"Architectural review response: {response}")
            
            return response

        except Exception as e:
            logger.error(f"Architectural review failed: {e}")
            # Return a safe fallback
            return {
                "module": "src/dewey/utils",
                "patterns": [],
                "concerns": ["Review failed"],
                "recommendations": []
            }

    def _classify_function(self, code: str) -> dict:
        """Classify a function's purpose and target module."""
        try:
            prompt = f"""Analyze this Python code and classify its functionality.
            
            Code:
            {code}
            
            Provide a JSON response with:
            {{
                "primary_category": "core|llm|pipeline|utils",
                "target_module": "Suggested target module path",
                "purpose": "Brief description of function purpose",
                "dependencies": ["List of key dependencies"]
            }}"""

            # Add timeout and lower temperature for more reliable responses
            response = self.llm.generate_response(
                prompt,
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"},
                strict_json=True
            )
            
            # Log the raw response for debugging
            logger.debug(f"Classification response: {response}")
            
            return response

        except Exception as e:
            logger.error(f"Function classification failed: {e}")
            # Return a safe fallback
            return {
                "primary_category": "utils",
                "target_module": "src/dewey/utils",
                "purpose": "Unknown (classification failed)",
                "dependencies": []
            }

    def _discover_modules(self, target_dir: str) -> dict:
        """Discover and analyze Python modules in the target directory."""
        try:
            # First get all Python files
            python_files = []
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if file.endswith('.py') and not file.endswith('_test.py'):
                        python_files.append(os.path.join(root, file))

            # Analyze each file
            file_summaries = []
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Get relative path for module name
                    rel_path = os.path.relpath(file_path, target_dir)
                    
                    # Basic file stats
                    loc = len(content.splitlines())
                    
                    # Try parsing with AST
                    try:
                        tree = ast.parse(content)
                        
                        # Extract imports
                        imports = []
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for name in node.names:
                                    imports.append(name.name)
                            elif isinstance(node, ast.ImportFrom):
                                module = node.module or ''
                                for name in node.names:
                                    imports.append(f"{module}.{name.name}")
                                    
                        # Count classes and functions
                        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                        
                        file_summary = {
                            'path': rel_path,
                            'loc': loc,
                            'classes': len(classes),
                            'functions': len(functions),
                            'imports': imports,
                            'docstring': ast.get_docstring(tree) or '',
                            'classes_info': []
                        }
                        
                        # Get detailed class info
                        for cls in classes:
                            methods = []
                            for node in ast.walk(cls):
                                if isinstance(node, ast.FunctionDef):
                                    methods.append({
                                        'name': node.name,
                                        'docstring': ast.get_docstring(node) or ''
                                    })
                                    
                            file_summary['classes_info'].append({
                                'name': cls.name,
                                'docstring': ast.get_docstring(cls) or '',
                                'methods': methods
                            })
                            
                        file_summaries.append(file_summary)
                        
                    except SyntaxError:
                        # Fallback for files with syntax errors
                        file_summaries.append({
                            'path': rel_path,
                            'loc': loc,
                            'error': 'Syntax error prevented full analysis'
                        })
                        
                except Exception as e:
                    logger.warning(f"Error analyzing {file_path}: {e}")
                    continue

            # Get directory structure analysis
            dir_analysis = self._analyze_directory_structure(file_summaries)
            
            # Calculate complexity metrics
            metrics = self._calculate_complexity_metrics(file_summaries)
            
            # Prepare analysis prompt
            prompt = f"""Please analyze this Python codebase and provide a detailed architectural assessment.

File Summaries:
{json.dumps(file_summaries, indent=2)}

Directory Structure:
{json.dumps(dir_analysis, indent=2)}

Complexity Metrics:
{json.dumps(metrics, indent=2)}

Provide a JSON response with:
1. Repository purpose and scope
2. Key components and their responsibilities
3. Architectural patterns identified
4. Dependency analysis
5. Architectural metrics (modularity, coupling, cohesion)
6. Validation issues and recommendations"""

            # Get initial analysis with fallback support
            initial_response = self.llm.generate_response(
                self._get_analysis_prompt()
            )
            
            # Parse response using LLMHandler
            initial_result = self.llm.parse_json_response(initial_response)
            
            # Refine with additional context
            context = {
                "file_count": len(file_summaries),
                "total_loc": sum(f.get('loc', 0) for f in file_summaries),
                "file_types": list(set(os.path.splitext(f['path'])[1] for f in file_summaries)),
                "dir_structure": dir_analysis,
                "complexity_metrics": metrics
            }
            
            refined = self._refine_analysis("module discovery", initial_result, context)
            
            # Log the architectural diagnostics
            self._log_architectural_diagnostics(refined)
            
            return refined
            
        except Exception as e:
            logger.error(f"Module discovery failed: {e}")
            return {}

    def _analyze_directory_structure(self, file_summaries: list) -> dict:
        """Analyze the directory structure of the codebase."""
        directory_structure = {}
        for summary in file_summaries:
            path_parts = summary["directory"].split(os.sep)
            current_dict = directory_structure
            for part in path_parts:
                if part:
                    current_dict = current_dict.setdefault(part, {})
        return directory_structure

    def _calculate_complexity_metrics(self, file_summaries: list) -> dict:
        """Calculate complexity metrics for the codebase."""
        total_classes = sum(s["complexity_indicators"]["class_count"] for s in file_summaries)
        total_functions = sum(s["complexity_indicators"]["function_count"] for s in file_summaries)
        total_imports = sum(s["complexity_indicators"]["import_count"] for s in file_summaries)
        total_loc = sum(s["complexity_indicators"]["loc"] for s in file_summaries)
        
        return {
            "total_files": len(file_summaries),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_imports": total_imports,
            "total_loc": total_loc,
            "avg_file_size": total_loc / len(file_summaries) if file_summaries else 0,
            "avg_complexity": {
                "classes_per_file": total_classes / len(file_summaries) if file_summaries else 0,
                "functions_per_file": total_functions / len(file_summaries) if file_summaries else 0,
                "imports_per_file": total_imports / len(file_summaries) if file_summaries else 0
            }
        }

    def _log_architectural_diagnostics(self, analysis: dict) -> None:
        """Log detailed diagnostics about the architectural analysis."""
        self.console.print("\n[bold]📊 Architectural Analysis Diagnostics:[/bold]")
        
        # Log identified patterns
        if "architecture_patterns" in analysis:
            self.console.print("\n[cyan]Identified Architecture Patterns:[/cyan]")
            for pattern in analysis["architecture_patterns"]:
                self.console.print(f"  • Pattern: {pattern['pattern']}")
                self.console.print(f"    Evidence: {pattern['evidence']}")
                self.console.print(f"    Benefits: {pattern['benefits']}")
                self.console.print(f"    Tradeoffs: {pattern['tradeoffs']}\n")
        
        # Log dependency analysis
        if "dependency_analysis" in analysis:
            self.console.print("[cyan]Dependency Analysis:[/cyan]")
            dep_analysis = analysis["dependency_analysis"]
            if "external_dependencies" in dep_analysis:
                self.console.print("  External Dependencies:")
                for dep in dep_analysis["external_dependencies"]:
                    self.console.print(f"    • {dep}")
            if "dependency_patterns" in dep_analysis:
                self.console.print("\n  Dependency Patterns:")
                for pattern in dep_analysis["dependency_patterns"]:
                    self.console.print(f"    • {pattern}")
        
        # Log architectural metrics
        if "architectural_metrics" in analysis:
            self.console.print("\n[cyan]Architectural Metrics:[/cyan]")
            metrics = analysis["architectural_metrics"]
            self.console.print(f"  • Modularity: {metrics['modularity']}")
            self.console.print(f"  • Coupling: {metrics['coupling']}")
            self.console.print(f"  • Cohesion: {metrics['cohesion']}")
            self.console.print(f"  • Complexity: {metrics['complexity']}")
        
        # Log validation issues
        if "validation" in analysis and "issues" in analysis["validation"]:
            self.console.print("\n[cyan]Architectural Issues:[/cyan]")
            for issue in analysis["validation"]["issues"]:
                self.console.print(f"\n  Issue: {issue['issue']}")
                self.console.print(f"  Severity: {issue['severity']}")
                self.console.print(f"  Impact: {issue['impact']}")
                self.console.print(f"  Recommendation: {issue['recommendation']}")
        
        # Log recommendations
        if "validation" in analysis and "recommendations" in analysis["validation"]:
            self.console.print("\n[cyan]Improvement Recommendations:[/cyan]")
            for rec in analysis["validation"]["recommendations"]:
                self.console.print(f"\n  Area: {rec['area']}")
                self.console.print(f"  Suggestion: {rec['suggestion']}")
                self.console.print(f"  Rationale: {rec['rationale']}")

    def _load_prd_config(self) -> dict:
        """Load PRD config from central dewey.yaml."""
        config_path = Path("/Users/srvo/dewey/config/dewey.yaml")
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found at {config_path}"
            )
        
        try:
            with open(config_path) as f:
                full_config = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            self.console.print(f"[yellow]⚠️ Config loading failed: {e} - Using defaults[/yellow]")
            full_config = {}

        prd_config = full_config.get("prd", {})
        
        return {
            "base_path": "/Users/srvo/dewey/config/prd",
            "active_prd": "current_prd.yaml",
            "schema": prd_config.get("schema", {
                "components": [{"name": "", "purpose": "", "dependencies": [], "interfaces": []}],
                "decisions": [{"timestamp": "datetime", "description": "", "alternatives": [], "rationale": ""}]
            }),
            "references": prd_config.get("references", {
                "conventions": "/Users/srvo/dewey/CONVENTIONS.md",
                "codebase_analysis": "/Users/srvo/dewey/docs/codebase_analysis.md"
            })
        }

    def _validate_prd_path(self) -> str:
        """
        Validates and returns the PRD file path following project conventions.
        The PRD must be stored in the 'docs' directory within the target directory.
        """
        # Get the directory name from the project root
        dir_name = os.path.basename(self.project_root)
        
        # Create docs directory if it doesn't exist
        docs_dir = os.path.join(self.project_root, 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        
        # Construct paths for both YAML and Markdown versions
        yaml_path = os.path.join(docs_dir, f'{dir_name}_Product_Requirements_Document.yaml')
        
        # Update central config to track PRD paths if not already tracked
        try:
            config_path = os.path.join(os.path.dirname(self.project_root), 'config', 'dewey.yaml')
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}
                
                if 'prd' not in config:
                    config['prd'] = {}
                if 'tracked_prds' not in config['prd']:
                    config['prd']['tracked_prds'] = []
                    
                # Add YAML path if not already tracked
                if yaml_path not in config['prd']['tracked_prds']:
                    config['prd']['tracked_prds'].append(yaml_path)
                    
                with open(config_path, 'w') as f:
                    yaml.safe_dump(config, f)
                    self.console.print(f"✓ Added PRD path to {config_path}")
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not update central config: {e}[/yellow]")
        
        self.console.print(f"✓ PRD path set to: {yaml_path}")
        return yaml_path

    def _load_conventions(self) -> dict:
        """Parse actual CONVENTIONS.md content."""
        # Use absolute path from project root per conventions
        conv_path = Path.home() / "dewey" / "CONVENTIONS.md"
        return self._parse_markdown_conventions(conv_path)

    def _parse_markdown_conventions(self, path: Path) -> dict:
        """Convert CONVENTIONS.md to structured data."""
        sections = {}
        current_section = None
        current_subsect = None
        
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("# "):
                current_section = line[2:].lower().replace(" ", "_")
                sections[current_section] = {}
                current_subsect = None
            elif line.startswith("## "):
                current_subsect = line[3:].lower().replace(" ", "_")
                sections[current_section][current_subsect] = []
            elif line.startswith("### "):
                continue  # Skip subsubsections for now
            else:
                if current_subsect:
                    sections[current_section][current_subsect].append(line)
                elif current_section:
                    sections[current_section].setdefault("content", []).append(line)
                    
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
        try:
            consolidated_dir = self.project_root / "consolidated_functions"
            if not consolidated_dir.exists():
                self.console.print("[yellow]No consolidated_functions directory found[/yellow]")
                return []
            return list(consolidated_dir.glob("consolidated_*.py"))
        except Exception as e:
            self.console.print(f"[yellow]Error finding consolidated functions: {e}[/yellow]")
            return []

    def _analyze_consolidated_function(self, path: Path) -> dict:
        """Analyze a consolidated function file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
                
            # Get function classification
            classification = self._classify_function(code)
            
            # Get architectural review
            review = self._architectural_review(code)
            
            # Combine analyses
            analysis = {
                'path': str(path),
                'classification': classification,
                'review': review,
                'code': code
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {path}: {e}")
            return {
                'path': str(path),
                'error': str(e)
            }

    def _handle_single_function(self, analysis: dict) -> None:
        """Process a single consolidated function."""
        try:
            # Get target module from architectural review
            target_module = analysis['review'].get('module', 'unknown')
            if target_module == 'unknown':
                self.console.print(f"[yellow]Could not determine target module for {analysis['path']}[/yellow]")
                return
                
            # Validate target location exists
            target_path = Path(self.project_root) / target_module
            if not self._validate_location(target_path):
                self.console.print(f"[red]Invalid target location: {target_path}[/red]")
                return
                
            # Reformat code for target module
            reformatted = self._reformat_code(analysis['code'], target_module)
            
            # Move the file
            self._move_function_file(Path(analysis['path']), target_module, analysis)
            
            # Update PRD for target module
            self._update_module_prd(target_module, analysis, {
                'code': reformatted,
                'path': analysis['path']
            })
            
            # Remove duplicate if successful
            self._remove_duplicate_code(analysis)
            
        except Exception as e:
            logger.error(f"Error handling function {analysis['path']}: {e}")

    def _update_module_prd(self, module: str, analysis: dict, func_info: dict) -> None:
        """Update the PRD for a module with consolidated function info."""
        try:
            # Load existing PRD if any
            prd_path = Path(self.project_root) / module / 'PRD.yaml'
            if prd_path.exists():
                with open(prd_path) as f:
                    prd = yaml.safe_load(f)
            else:
                prd = {}
                
            # Add function info
            if 'functions' not in prd:
                prd['functions'] = []
                
            func_entry = {
                'name': Path(func_info['path']).stem,
                'path': func_info['path'],
                'description': analysis['classification'].get('purpose', ''),
                'inputs': analysis['classification'].get('inputs', []),
                'output': analysis['classification'].get('output', ''),
                'complexity': analysis['classification'].get('complexity', 'unknown'),
                'dependencies': analysis['classification'].get('dependencies', []),
                'architectural_notes': analysis['review'].get('concerns', [])
            }
            
            # Check if function already exists
            existing = next(
                (f for f in prd['functions'] if f['name'] == func_entry['name']),
                None
            )
            
            if existing:
                # Update existing entry
                existing.update(func_entry)
            else:
                # Add new entry
                prd['functions'].append(func_entry)
                
            # Save updated PRD
            with open(prd_path, 'w') as f:
                yaml.safe_dump(prd, f, sort_keys=False)
                
        except Exception as e:
            logger.error(f"Error updating PRD for {module}: {e}")

    def _validate_location(self, proposed_path: Path) -> bool:
        """Ensure path matches project conventions."""
        parts = proposed_path.parts
        if "llm" in parts and "api_clients" not in parts:
            msg = "LLM components must be in llm/api_clients/ per CONVENTIONS.md"
            raise typer.BadParameter(
                msg,
            )
        return True

    def _get_similar_components(self, query: str) -> list:
        """Find related components by module name."""
        return [m for m in self.modules if query.lower() in m.get("purpose", "").lower()]

    def process_consolidated_functions(self) -> None:
        """Process all consolidated functions interactively."""
        self.console.print("[bold]Consolidated Function Relocation[/]")
        consolidated_files = self._find_consolidated_functions()

        for func_file in consolidated_files:
            try:
                analysis = {
                    "path": func_file,
                    "name": func_file.stem.replace("consolidated_", ""),
                    "content": func_file.read_text(),
                }
                self._handle_single_function(analysis)
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Error processing {func_file}: {e}[/yellow]")
                continue

    def _reformat_code(self, content: str, target_module: str) -> str:
        """Reformat code using LLM."""
        try:
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

            # Add timeout and lower temperature for more reliable responses
            response = self.llm.generate_response(
                prompt,
                temperature=0.1,
                max_tokens=4000
            )
            
            # Log success
            logger.info(f"Successfully reformatted code for {target_module}")
            
            return response

        except Exception as e:
            logger.warning(f"Code reformatting failed: {e}")
            # Return original content if reformatting fails
            return content

    def _move_function_file(
        self, src: Path, target_module: str, func_info: dict
    ) -> None:
        """Move and reformat file with LLM-powered cleanup."""
        target_dir = self.project_root / "src" / "dewey" / target_module
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
            f"✅ Moved to: [bold green]{dest_path.relative_to(self.project_root)}[/]"
        )
        self.console.print(
            f"📏 Size change: {len(original_content)} → {len(reformed_content)} chars"
        )

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
        for path in self.project_root.glob("src/dewey/**/*.py"):
            if path.read_text() == analysis["content"] and path != analysis["path"]:
                similar.append(path)
                
        if similar:
            self.console.print(f"Found {len(similar)} exact duplicates:")
            for path in similar:
                self.console.print(f" - {path.relative_to(self.project_root)}")

            if Confirm.ask("Delete duplicates?"):
                for path in similar:
                    path.unlink()
                    self.console.print(f"🗑️ Deleted: {path}")

    def _determine_target_directory(self, func_info: dict) -> str:
        """Determine target directory based on function classification."""
        try:
            return func_info.get("primary_category", "utils")
        except Exception as e:
            self.console.print(f"[yellow]Error determining target directory: {e}[/yellow]")
            return "utils"

    def interactive_builder(self) -> None:
        """Guided PRD creation with validation."""
        try:
            self.console.print("[bold cyan]PRD Builder[/bold cyan]\n")
            
            # Initialize with high-level requirements
            self._gather_overview()
            self._process_components()
            self._process_decisions()
            self._finalize_prd()
            
            self._save_prd()
            self._generate_docs()
            self.console.print("\n[bold green]✅ PRD generation complete![/bold green]")
        except Exception as e:
            self.console.print(f"[red]Error during PRD building: {e}[/red]")

    def _gather_overview(self) -> None:
        """Collect high-level PRD information."""
        self.console.print("[bold]Step 1/4: Project Overview[/bold]")
        
        if not self.modules:
            self.console.print("[yellow]No modules found to analyze[/yellow]")
            return
            
        try:
            analysis = self.modules  # We now have just one comprehensive analysis
            
            self.prd_data["title"] = Prompt.ask(
                "Project title", 
                default=self.prd_data.get("title", "Untitled Project")
            )
            
            # Use repository_purpose if available, otherwise prompt user
            if isinstance(analysis, dict) and "repository_purpose" in analysis:
                self.prd_data["description"] = analysis["repository_purpose"]
            else:
                self.prd_data["description"] = Prompt.ask(
                    "Project description",
                    default="No description available"
                )
            
            self.console.print("\n[bold]Repository Analysis:[/bold]")
            if isinstance(analysis, dict):
                self.console.print(f"  Purpose: {analysis.get('repository_purpose', 'Unknown')}")
                
                if analysis.get("key_components"):
                    self.console.print("\n[bold]Key Components:[/bold]")
                    for component in analysis["key_components"]:
                        name = component.get("name", "Unknown")
                        purpose = component.get("purpose", "No purpose specified")
                        self.console.print(f"  • {name} - {purpose}")
                        
                if analysis.get("architecture_patterns"):
                    self.console.print("\n[bold]Architecture Patterns:[/bold]")
                    for pattern in analysis["architecture_patterns"]:
                        self.console.print(f"  • {pattern}")
            else:
                self.console.print("[yellow]Could not analyze repository structure[/yellow]")
                
        except Exception as e:
            self.console.print(f"[yellow]Error during overview generation: {e}[/yellow]")
            # Ensure we at least have basic information
            if "title" not in self.prd_data:
                self.prd_data["title"] = Prompt.ask(
                    "Project title",
                    default="Untitled Project"
                )
            if "description" not in self.prd_data:
                self.prd_data["description"] = Prompt.ask(
                    "Project description",
                    default="No description available"
                )

    def _process_components(self) -> None:
        """Process and document core components."""
        if 'components' not in self.prd_data:
            self.prd_data['components'] = {}
        
        total = len(self.components)
        processed = 0
        
        if total == 0:
            self.console.print("[yellow]No components found to process[/yellow]")
            return
            
        for component in self.components:
            processed += 1
            self.console.print(f"\n📦 Processing component {processed}/{total}: '{component}'")
            
            # Get component info
            description = self.component_descriptions.get(component, 'No description available')
            responsibilities = self.component_responsibilities.get(component, [])
            dependencies = self.component_dependencies.get(component, [])
            
            self.console.print(f"  Description: {description}")
            if responsibilities:
                self.console.print("  Responsibilities:")
                for resp in responsibilities:
                    self.console.print(f"    • {resp}")
            
            if self.console.input("  Include this component? [y/n]: ").lower() == 'y':
                self.prd_data['components'][component] = {
                    'description': description,
                    'responsibilities': responsibilities,
                    'dependencies': dependencies
                }
                self.console.print(f"  ✅ Added component: {component}")
            
        self.console.print(f"\n✅ Processed {processed} components")

    def _process_decisions(self) -> None:
        """Process and document architectural decisions."""
        if 'decisions' not in self.prd_data:
            self.prd_data['decisions'] = {
                'patterns': [],
                'issues': []
            }
        
        # Process critical issues
        self.console.print("\n[bold]Analyzing Current Architecture:[/bold]")
        try:
            total_issues = len(self.critical_issues)
            processed_issues = 0
            
            for issue in self.critical_issues:
                processed_issues += 1
                self.console.print(f"\n🔍 Processing issue {processed_issues}/{total_issues}: '{issue}'")
                
                if self.console.input("  Document this issue? [y/n]: ").lower() == 'y':
                    self.console.print("  ⏳ Analyzing issue impact...")
                    issue_data = {
                        'title': issue,
                        'impact': self.issue_impacts.get(issue, ''),
                        'required_change': self.issue_changes.get(issue, ''),
                        'priority': self.issue_priorities.get(issue, 'Medium')
                    }
                    self.prd_data['decisions']['issues'].append(issue_data)
                    self.console.print(f"  ✅ Added architectural issue: {issue}")
                
            self.console.print(f"\n✅ Processed {processed_issues} issues")
            
        except Exception as e:
            self.console.print(f"[red]❌ Error analyzing architectural issues: {e}[/red]")
            return
        
        # Process architecture patterns
        self.console.print("\n[bold]Processing Architecture Patterns:[/bold]")
        try:
            total_patterns = len(self.architecture_patterns)
            processed_patterns = 0
            
            for pattern in self.architecture_patterns:
                processed_patterns += 1
                self.console.print(f"\n🏛️  Processing pattern {processed_patterns}/{total_patterns}: '{pattern}'")
                
                if self.console.input("  Document this pattern? [y/n]: ").lower() == 'y':
                    self.prd_data['decisions']['patterns'].append(pattern)
                    self.console.print(f"  ✅ Added architectural pattern: {pattern}")
                
            self.console.print(f"\n✅ Processed {processed_patterns} patterns")
            
        except Exception as e:
            self.console.print(f"[red]❌ Error documenting architecture patterns: {e}[/red]")
            return

    def _finalize_prd(self) -> None:
        """Final polish and validation of the PRD."""
        self.console.print("\nStep 4/4: Final Polish")
        
        try:
            # Get initial analysis with fallback support
            initial_response = self.llm.generate_response(
                self._get_analysis_prompt()
            )
            
            # Parse response using LLMHandler
            initial_result = self.llm.parse_json_response(initial_response)
            
            # Prepare context for refinement
            context = self._prepare_refinement_context()
            
            # Refine the analysis
            refined_result = self._refine_analysis(
                "PRD finalization",
                initial_result,
                context
            )
            
            # Update PRD with refined analysis
            if "executive_summary" in refined_result:
                self.prd_data['executive_summary'] = refined_result["executive_summary"]
                self.console.print("  ✅ Executive summary generated")
                
                # Handle convention issues
                self._handle_convention_issues(refined_result)
                
                # Display improvement suggestions
                self._display_improvements(refined_result)
                
        except json.JSONDecodeError:
            self.console.print("[yellow]Error parsing LLM response[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error during PRD finalization: {e}[/red]")
        finally:
            # Always try to save the PRD
            self._save_prd()

    def _get_analysis_prompt(self) -> str:
        """Generate the analysis prompt."""
        return f"""Analyze and enhance this PRD:

PRD Content:
{json.dumps(self.prd_data, indent=2)}

Project Conventions:
{json.dumps(self.conventions, indent=2)}

Provide a JSON response with:
{{
    "executive_summary": "A 2-3 paragraph summary covering project purpose, key components, and major architectural decisions",
    "convention_issues": [
        {{
            "issue": "Description of the convention violation",
            "fix": "Suggested fix to resolve the issue"
        }}
    ],
    "suggested_improvements": [
        "List of general improvements that could enhance the PRD"
    ]
}}"""

    def _prepare_refinement_context(self) -> dict:
        """Prepare context for refinement."""
        return {
            "total_components": len(self.prd_data.get("components", {})),
            "total_decisions": len(self.prd_data.get("decisions", {}).get("issues", [])),
            "architecture_patterns": self.prd_data.get("decisions", {}).get("patterns", []),
            "metadata": self.prd_data.get("metadata", {})
        }

    def _handle_convention_issues(self, refined_result: dict) -> None:
        """Handle convention issues from the analysis."""
        if "convention_issues" in refined_result and refined_result["convention_issues"]:
            self.console.print("\n[yellow]Convention Issues Found:[/yellow]")
            for issue in refined_result["convention_issues"]:
                self.console.print(f"  • {issue['issue']}")
                self.console.print(f"    Fix: {issue['fix']}")
            
            if self.console.input("\nAttempt automatic fixes? [y/n]: ").lower() == 'y':
                self._apply_convention_fixes(refined_result["convention_issues"])
        else:
            self.console.print("  ✅ No convention issues found")

    def _display_improvements(self, refined_result: dict) -> None:
        """Display improvement suggestions."""
        if "suggested_improvements" in refined_result and refined_result["suggested_improvements"]:
            self.console.print("\n[bold]Suggested Improvements:[/bold]")
            for suggestion in refined_result["suggested_improvements"]:
                self.console.print(f"  • {suggestion}")

    def _apply_convention_fixes(self, issues: list) -> None:
        """Apply fixes for convention issues."""
        try:
            # Create a prompt that includes both the current PRD and the specific fixes to apply
            prompt = f"""Fix the following PRD according to these specific issues:

Current PRD:
{json.dumps(self.prd_data, indent=2)}

Issues to Fix:
{json.dumps(issues, indent=2)}

Return ONLY a valid JSON object containing the fixed PRD content.
Do not include any other text or explanations."""

            response = self.llm.generate_response(
                prompt,
                temperature=0.2
            )
            
            try:
                fixed_prd = json.loads(response)
                
                # Validate the fixed PRD has required sections
                required_sections = {"title", "description", "components", "decisions"}
                if all(section in fixed_prd for section in required_sections):
                    self.prd_data = fixed_prd
                    self.console.print("[green]Successfully applied convention fixes[/green]")
                else:
                    self.console.print("[yellow]Fixed PRD is missing required sections[/yellow]")
                    self.console.print("[yellow]Keeping original PRD content[/yellow]")
                    
            except json.JSONDecodeError:
                self.console.print("[yellow]Error parsing fixed PRD[/yellow]")
                self.console.print("[yellow]Keeping original PRD content[/yellow]")
                
        except Exception as e:
            self.console.print(f"[yellow]Error applying convention fixes: {e}[/yellow]")
            self.console.print("[yellow]Keeping original PRD content[/yellow]")

    def _generate_executive_summary(self) -> bool:
        """Generate an executive summary for the PRD."""
        try:
            prompt = f"""Please generate an executive summary for this PRD.

            Current PRD Data:
            {json.dumps(self.prd_data, indent=2)}

            Components:
            {json.dumps(self.components, indent=2)}

            Architecture Patterns:
            {json.dumps(self.architecture_patterns, indent=2)}

            Critical Issues:
            {json.dumps(self.critical_issues, indent=2)}

            Provide a JSON response with:
            1. Overview of project scope and goals
            2. Key architectural decisions and patterns
            3. Major components and their interactions
            4. Critical issues and mitigation strategies
            5. Next steps and recommendations"""

            # Add timeout and lower temperature for more reliable responses
            response = self.llm.generate_response(
                prompt,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},
                strict_json=True
            )
            
            # Log the raw response for debugging
            logger.debug(f"Executive summary response: {response}")
            
            # Update PRD with summary
            self.prd_data['executive_summary'] = response
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return False

    def _validate_conformance(self) -> list[str]:
        """Validate PRD conformance to conventions."""
        try:
            prompt = f"""Please validate this PRD against the provided conventions.

            PRD Content:
            {json.dumps(self.prd_data, indent=2)}

            Conventions:
            {json.dumps(self.conventions, indent=2)}

            Provide a JSON response with:
            1. List of validation issues
            2. Severity level for each issue
            3. Suggested fixes
            4. Impact assessment"""

            # Add timeout and lower temperature for more reliable responses
            response = self.llm.generate_response(
                prompt,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},
                strict_json=True
            )
            
            # Log the raw response for debugging
            logger.debug(f"Validation response: {response}")
            
            # Extract issues that need fixing
            validation = response
            issues = []
            for issue in validation.get('issues', []):
                if issue.get('severity', 'low').lower() in ['high', 'medium']:
                    issues.append(issue)
                    
            return issues
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return []

    def _apply_convention_fixes(self, issues: list) -> None:
        """Apply automated fixes for convention issues."""
        try:
            for issue in issues:
                prompt = f"""Please provide a fix for this PRD convention issue.

Issue:
{json.dumps(issue, indent=2)}

Current PRD:
{json.dumps(self.prd_data, indent=2)}

Provide a JSON response with:
1. Updated section of the PRD
2. List of changes made
3. Verification steps"""

                response = self.llm.generate_response(
                    prompt,
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                # Parse response using LLMHandler
                fix = self.llm.parse_json_response(response)
                
                # Apply the fix if provided
                if 'updated_section' in fix:
                    section = issue.get('section')
                    if section in self.prd_data:
                        self.prd_data[section] = fix['updated_section']
                        logger.info(f"Applied fix to section: {section}")
                        
        except Exception as e:
            logger.error(f"Failed to apply convention fixes: {e}")

    def _generate_docs(self) -> None:
        """Generate documentation from the PRD."""
        try:
            prompt = f"""Please generate comprehensive documentation from this PRD.

PRD Content:
{json.dumps(self.prd_data, indent=2)}

Components:
{json.dumps(self.components, indent=2)}

Architecture:
{json.dumps(self.architecture_patterns, indent=2)}

Provide a JSON response with:
1. README.md content
2. API documentation
3. Architecture overview
4. Component documentation
5. Setup instructions"""

            response = self.llm.generate_response(
                prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse response using LLMHandler
            docs = self.llm.parse_json_response(response)
            
            # Generate documentation files
            docs_dir = Path(self.project_root) / 'docs'
            docs_dir.mkdir(exist_ok=True)
            
            # Write README
            if 'readme' in docs:
                with open(docs_dir / 'README.md', 'w') as f:
                    f.write(docs['readme'])
                    
            # Write API docs
            if 'api' in docs:
                with open(docs_dir / 'API.md', 'w') as f:
                    f.write(docs['api'])
                    
            # Write architecture docs
            if 'architecture' in docs:
                with open(docs_dir / 'ARCHITECTURE.md', 'w') as f:
                    f.write(docs['architecture'])
                    
            # Write component docs
            if 'components' in docs:
                components_dir = docs_dir / 'components'
                components_dir.mkdir(exist_ok=True)
                for name, content in docs['components'].items():
                    with open(components_dir / f"{name}.md", 'w') as f:
                        f.write(content)
                        
            # Write setup instructions
            if 'setup' in docs:
                with open(docs_dir / 'SETUP.md', 'w') as f:
                    f.write(docs['setup'])
                    
            logger.info("Generated documentation files")
            
        except Exception as e:
            logger.error(f"Failed to generate documentation: {e}")

    def build_prd(self) -> None:
        """Build a new PRD from scratch."""
        try:
            self.console.print("\n[bold cyan]🚀 Starting PRD Builder[/bold cyan]\n")
            
            # Step 1: Repository Analysis
            self.console.print("[bold]📊 Step 1/4: Analyzing Repository Structure[/bold]")
            self.console.print("  ⏳ Scanning files and directories...")
            self._analyze_repository()
            self.console.print("  ✅ Repository analysis complete\n")
            
            # Print initialization info
            self.console.print(f"[dim]Project Details:[/dim]")
            self.console.print(f"  📁 Project Root: {self.project_root}")
            self.console.print(f"  📄 PRD Path: {self.prd_path}\n")
            
            # Step 2: Project Overview
            self.console.print("[bold]📝 Step 2/4: Gathering Project Overview[/bold]")
            title = self.console.input("  📌 Project title: ")
            if title:
                self.prd_data["title"] = title
            
            # Print repository analysis results
            if isinstance(self.modules, dict):
                self.console.print("\n[bold]Repository Analysis Results:[/bold]")
                if "repository_purpose" in self.modules:
                    self.console.print(f"  🎯 Purpose: {self.modules['repository_purpose']}\n")
                
                if "key_components" in self.modules:
                    self.console.print("[bold]Key Components:[/bold]")
                    for component in self.modules["key_components"]:
                        name = component.get("name", "Unknown")
                        purpose = component.get("purpose", "No purpose specified")
                        self.console.print(f"  • {name}")
                        self.console.print(f"    {purpose}")
                    self.console.print()
            
            # Step 3: Core Components
            self.console.print("[bold]🔧 Step 3/4: Processing Core Components[/bold]")
            self._process_components()
            
            # Step 4: Architectural Decisions
            self.console.print("[bold]🏗️  Step 4/4: Documenting Architectural Decisions[/bold]")
            self._process_decisions()
            
            # Final Steps
            self.console.print("\n[bold]📋 Final Steps[/bold]")
            
            # Generate executive summary
            self.console.print("  ⏳ Generating executive summary...")
            if self._generate_executive_summary():
                self.console.print("  ✅ Executive summary generated")
            
            # Validate against conventions
            self.console.print("  ⏳ Validating against conventions...")
            issues = self._validate_conformance()
            if issues:
                self.console.print("\n[yellow]Convention Issues Found:[/yellow]")
                for issue in issues:
                    self.console.print(f"  • {issue}")
                
                if self.console.input("\nAttempt automatic fixes? [y/n]: ").lower() == 'y':
                    self.console.print("  ⏳ Applying convention fixes...")
                    self._apply_convention_fixes(issues)
            else:
                self.console.print("  ✅ No convention issues found")
            
            # Save PRD
            self.console.print("  ⏳ Saving PRD files...")
            self._save_prd()
            
            self.console.print("\n[bold green]✅ PRD generation complete![/bold green]")
            
        except Exception as e:
            self.console.print(f"\n[bold red]❌ Error during PRD building:[/bold red]")
            self.console.print(f"[red]{str(e)}[/red]")
            raise

    def update_prd(self) -> None:
        """Update an existing PRD with new information while preserving existing content."""
        try:
            self.console.print("\n[bold cyan]🔄 Starting PRD Update[/bold cyan]\n")
            
            # Load existing PRD
            try:
                with open(self.prd_path) as f:
                    existing_prd = yaml.safe_load(f) or {}
                self.prd_data = existing_prd
                self.console.print("✅ Loaded existing PRD")
            except Exception as e:
                self.console.print(f"[red]Error loading existing PRD: {e}[/red]")
                return
            
            # Step 1: Repository Analysis
            self.console.print("[bold]📊 Step 1/4: Analyzing Repository Changes[/bold]")
            self.console.print("  ⏳ Scanning for new components...")
            self._analyze_repository()
            self.console.print("  ✅ Repository analysis complete\n")
            
            # Print current state
            self.console.print(f"[dim]Project Details:[/dim]")
            self.console.print(f"  📁 Project Root: {self.project_root}")
            self.console.print(f"  📄 PRD Path: {self.prd_path}")
            self.console.print(f"  📝 Current Version: {self.prd_data.get('metadata', {}).get('version', 'N/A')}\n")
            
            # Step 2: Update Project Overview
            self.console.print("[bold]📝 Step 2/4: Reviewing Project Overview[/bold]")
            if self.console.input("  Update project title? [y/n]: ").lower() == 'y':
                title = self.console.input("  📌 New project title: ")
                if title:
                    self.prd_data["title"] = title
            
            # Print repository analysis results
            if isinstance(self.modules, dict):
                self.console.print("\n[bold]Repository Analysis Results:[/bold]")
                if "repository_purpose" in self.modules:
                    self.console.print(f"  🎯 Purpose: {self.modules['repository_purpose']}\n")
                
                if "key_components" in self.modules:
                    self.console.print("[bold]Key Components:[/bold]")
                    for component in self.modules["key_components"]:
                        name = component.get("name", "Unknown")
                        purpose = component.get("purpose", "No purpose specified")
                        self.console.print(f"  • {name}")
                        self.console.print(f"    {purpose}")
                    self.console.print()
            
            # Step 3: Update Components
            self.console.print("[bold]🔧 Step 3/4: Updating Components[/bold]")
            self._process_components()
            
            # Step 4: Update Architectural Decisions
            self.console.print("[bold]🏗️  Step 4/4: Updating Architectural Decisions[/bold]")
            self._process_decisions()
            
            # Final Steps
            self.console.print("\n[bold]📋 Final Steps[/bold]")
            
            # Update version history
            if 'metadata' not in self.prd_data:
                self.prd_data['metadata'] = {}
            if 'version_history' not in self.prd_data['metadata']:
                self.prd_data['metadata']['version_history'] = []
                
            # Add new version entry
            from datetime import datetime
            version_entry = {
                'version': f"{len(self.prd_data['metadata']['version_history']) + 1}.0",
                'date': datetime.now().strftime('%Y-%m-%d'),
                'author': os.getenv('USER', 'unknown'),
                'changes': 'Updated PRD with latest repository analysis'
            }
            self.prd_data['metadata']['version_history'].append(version_entry)
            
            # Validate against conventions
            self.console.print("  ⏳ Validating against conventions...")
            issues = self._validate_conformance()
            if issues:
                self.console.print("\n[yellow]Convention Issues Found:[/yellow]")
                for issue in issues:
                    self.console.print(f"  • {issue}")
                
                if self.console.input("\nAttempt automatic fixes? [y/n]: ").lower() == 'y':
                    self.console.print("  ⏳ Applying convention fixes...")
                    self._apply_convention_fixes(issues)
            else:
                self.console.print("  ✅ No convention issues found")
            
            # Save updated PRD
            self.console.print("  ⏳ Saving PRD files...")
            self._save_prd()
            
            self.console.print("\n[bold green]✅ PRD update complete![/bold green]")
            
        except Exception as e:
            self.console.print(f"\n[bold red]❌ Error during PRD update:[/bold red]")
            self.console.print(f"[red]{str(e)}[/red]")
            raise

    def _save_prd(self) -> None:
        """Save the PRD to both YAML and Markdown formats."""
        try:
            if not self.prd_path:
                self.prd_path = self._validate_prd_path()
                
            # Ensure docs directory exists
            docs_dir = os.path.dirname(self.prd_path)
            os.makedirs(docs_dir, exist_ok=True)
            
            # Get base name without extension
            base_name = os.path.splitext(os.path.basename(self.prd_path))[0]
            
            # Ensure architecture patterns are included in decisions
            if 'decisions' not in self.prd_data:
                self.prd_data['decisions'] = {}
            if 'patterns' not in self.prd_data['decisions']:
                self.prd_data['decisions']['patterns'] = []
            
            # Add discovered architecture patterns
            self.prd_data['decisions']['patterns'] = list(set(
                self.prd_data['decisions']['patterns'] + self.architecture_patterns
            ))
            
            # Save YAML version
            with open(self.prd_path, "w") as f:
                yaml.dump(self.prd_data, f, default_flow_style=False, sort_keys=False)
            
            # Generate and save Markdown version
            md_path = os.path.splitext(self.prd_path)[0] + ".md"
            with open(md_path, "w") as f:
                # Title and Description
                f.write(f"# {self.prd_data.get('title', 'Product Requirements Document')}\n\n")
                f.write(f"{self.prd_data.get('description', '')}\n\n")
                
                # Executive Summary
                if 'executive_summary' in self.prd_data:
                    f.write("## Executive Summary\n\n")
                    f.write(f"{self.prd_data['executive_summary']}\n\n")
                
                # Components
                f.write("## Components\n\n")
                components = self.prd_data.get('components', {})
                for name, details in components.items():
                    f.write(f"### {name}\n\n")
                    if isinstance(details, dict):
                        if 'description' in details:
                            f.write(f"{details['description']}\n\n")
                        if 'responsibilities' in details:
                            f.write("#### Responsibilities\n\n")
                            for resp in details['responsibilities']:
                                f.write(f"- {resp}\n")
                            f.write("\n")
                        if 'dependencies' in details:
                            f.write("#### Dependencies\n\n")
                            for dep in details['dependencies']:
                                f.write(f"- {dep}\n")
                            f.write("\n")
                
                # Architectural Decisions
                if 'decisions' in self.prd_data:
                    f.write("## Architectural Decisions\n\n")
                    decisions = self.prd_data['decisions']
                    
                    if 'patterns' in decisions and decisions['patterns']:
                        f.write("### Architecture Patterns\n\n")
                        for pattern in decisions['patterns']:
                            f.write(f"- {pattern}\n")
                        f.write("\n")
                        
                    if 'issues' in decisions and decisions['issues']:
                        f.write("### Critical Issues\n\n")
                        for issue in decisions['issues']:
                            f.write(f"#### {issue['title']}\n\n")
                            f.write(f"**Impact:** {issue.get('impact', 'Not specified')}\n\n")
                            f.write(f"**Required Change:** {issue.get('required_change', 'Not specified')}\n\n")
                            f.write(f"**Priority:** {issue.get('priority', 'Medium')}\n\n")
                
            self.console.print(f"\n✅ Saved PRD to:")
            self.console.print(f"  • YAML: {self.prd_path}")
            self.console.print(f"  • Markdown: {md_path}")
            
        except Exception as e:
            self.console.print(f"\n[bold red]❌ Error saving PRD:[/bold red] {str(e)}")
            raise

    def _format_stakeholders(self, stakeholders: list) -> str:
        """Format stakeholder information into markdown."""
        if not stakeholders:
            return "No stakeholders specified."
            
        sections = []
        for stakeholder in stakeholders:
            sections.append(f"""- **{stakeholder.get('name', 'Unknown')}**
  - Role: {stakeholder.get('role', 'Unspecified')}
  - Contact: {stakeholder.get('contact', 'No contact information')}
  - Last Review: {stakeholder.get('review_date', 'Not reviewed')}""")
            
        return "\n".join(sections)

    def _format_components(self) -> str:
        """Format components section with improved markdown."""
        if not self.prd_data.get("components"):
            return "No components documented."
            
        sections = []
        for comp in self.prd_data["components"]:
            sections.append(f"""### {comp['name']}
- **Purpose:** {comp['purpose']}
- **Dependencies:**
  {self._format_list(comp['dependencies']) if comp['dependencies'] else '  - None'}""")
            
        return "\n\n".join(sections)

    def _format_decisions(self) -> str:
        """Format architectural decisions with improved markdown."""
        if not self.prd_data.get("decisions"):
            return "No architectural decisions documented."
            
        # Group decisions by status
        decisions_by_status = {
            "Required Change": [],
            "Current Implementation": [],
            "Planned Enhancement": []
        }
        
        for decision in self.prd_data["decisions"]:
            status = decision.get("status", "Current Implementation")
            decisions_by_status[status].append(decision)
            
        sections = []
        
        # Format Required Changes first
        if decisions_by_status["Required Change"]:
            sections.append("### Required Architectural Changes")
            for decision in decisions_by_status["Required Change"]:
                sections.append(f"""#### {decision['description']}
**Priority:** {decision.get('priority', 'Not specified')}

**Current Impact:**
{decision.get('current_impact', 'Not specified')}

**Required Change:**
{decision.get('required_change', 'Not specified')}

**Implementation Steps:**
{self._format_list(decision.get('implementation_steps', []))}

**Rationale:**
{decision['rationale']}

**Alternatives Considered:**
{self._format_list(decision['alternatives'])}

**Impacted Components:**
{self._format_list(decision['impacted_components'])}""")
        
        # Format Current Implementations
        if decisions_by_status["Current Implementation"]:
            sections.append("### Current Architecture")
            for decision in decisions_by_status["Current Implementation"]:
                sections.append(f"""#### {decision['description']}
**Rationale:**
{decision['rationale']}

**Alternatives Considered:**
{self._format_list(decision['alternatives'])}

**Impacted Components:**
{self._format_list(decision['impacted_components'])}

**Tradeoffs:**
{self._format_list(decision.get('tradeoffs', []))}""")
        
        # Format Planned Enhancements
        if decisions_by_status["Planned Enhancement"]:
            sections.append("### Planned Architectural Enhancements")
            for decision in decisions_by_status["Planned Enhancement"]:
                sections.append(f"""#### {decision['description']}
**Priority:** {decision.get('priority', 'Not specified')}

**Current Impact:**
{decision.get('current_impact', 'Not specified')}

**Planned Change:**
{decision.get('required_change', 'Not specified')}

**Implementation Steps:**
{self._format_list(decision.get('implementation_steps', []))}

**Rationale:**
{decision['rationale']}

**Alternatives Considered:**
{self._format_list(decision['alternatives'])}

**Impacted Components:**
{self._format_list(decision['impacted_components'])}""")
        
        return "\n\n".join(sections)

    def _format_requirements(self, requirements: list) -> str:
        """Format requirements with improved markdown."""
        if not requirements:
            return "No requirements specified."
            
        sections = []
        for req in requirements:
            sections.append(f"""#### {req.get('description', 'Unnamed Requirement')}
- **Implementation:** {req.get('implementation_code', 'Not implemented')}
- **Complexity:** {req.get('complexity', 'Unknown')}
- **LLM Validated:** {req.get('llm_validated', False)}""")
            
        return "\n\n".join(sections)

    def _format_list(self, items: list | None) -> str:
        """Format a list of items as markdown bullet points."""
        if not items:
            return "- None specified"
        if isinstance(items, dict):
            return "\n".join(f"- {key}: {value}" for key, value in items.items())
        return "\n".join(f"- {item}" for item in items)

    def _format_version_history(self) -> str:
        """Format version history as a markdown table."""
        history = self.prd_data.get('metadata', {}).get('version_history', [])
        if not history:
            return "No version history available."
            
        table = "| Version | Date | Author | Changes |\n|---------|------|--------|----------|\n"
        for version in history:
            table += f"| {version.get('version', 'N/A')} | {version.get('date', 'N/A')} | "
            table += f"{version.get('author', 'N/A')} | {version.get('changes', 'N/A')} |\n"
            
        return table

class LLMError(Exception):
    """Exception raised for LLM-related errors."""
    pass

def main():
    """Main entry point for PRD builder."""
    parser = argparse.ArgumentParser(description="Build or update PRD documentation")
    parser.add_argument("command", choices=["init", "update"], help="Command to execute")
    parser.add_argument("target_dir", help="Target directory for PRD")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    try:
        # Validate target directory
        target_dir = Path(args.target_dir)
        if not target_dir.exists() or not target_dir.is_dir():
            logger.error(f"Target directory does not exist or is not a directory: {target_dir}")
            sys.exit(1)

        # Create necessary directories
        docs_dir = target_dir / "docs"
        os.makedirs(docs_dir, exist_ok=True)

        # Determine PRD path
        prd_path = None
        if args.command == "update":
            # For update, look for existing PRD
            prd_path = docs_dir / f"{target_dir.name}_Product_Requirements_Document.yaml"
            if not prd_path.exists():
                logger.error(f"PRD file not found at {prd_path}")
                sys.exit(1)
        else:
            # For init, we'll let PRDManager create the path
            prd_path = None

        # Load configuration
        try:
            config = load_config()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

        # Initialize LLM with retry mechanism
        max_llm_retries = 3
        llm = None
        for attempt in range(max_llm_retries):
            try:
                llm = LLMHandler(config.get("llm", {}))
                # Test LLM connection with a simple prompt
                test_response = llm.generate_response(
                    "Return the word 'OK' if you can read this.",
                    temperature=0.1
                )
                if "OK" in test_response:
                    logger.info("Successfully tested LLM connection")
                    break
                else:
                    raise LLMError("Unexpected response from LLM test")
            except Exception as e:
                if attempt < max_llm_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(f"LLM initialization attempt {attempt + 1} failed: {e}")
                    logger.info(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to initialize LLM after {max_llm_retries} attempts: {e}")
                    sys.exit(1)

        # Initialize PRD manager
        try:
            prd_manager = PRDManager(
                project_root=str(target_dir),
                prd_path=str(prd_path) if prd_path else None,
                llm=llm
            )
        except Exception as e:
            logger.error(f"Failed to initialize PRD Manager: {e}")
            sys.exit(1)

        # Execute command
        try:
            if args.command == "init":
                logger.info("Starting PRD initialization...")
                prd_manager.build_prd()
            else:
                logger.info("Starting PRD update...")
                prd_manager.update_prd()
                
            logger.info("PRD operation completed successfully")
            
        except LLMError as e:
            if "Circuit breaker open" in str(e):
                logger.error(
                    "Rate limit circuit breaker triggered. Please wait a few minutes "
                    "before trying again. The system needs time to cool down."
                )
            elif "Rate limit" in str(e):
                logger.error(
                    "Rate limit reached. Please wait a few minutes before trying again. "
                    "Consider using a different model or reducing the number of concurrent requests."
                )
            else:
                logger.error(f"LLM error occurred: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Detailed traceback:")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Detailed traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main()
