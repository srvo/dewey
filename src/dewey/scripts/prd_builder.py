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
            # Initial analysis with flash-lite
            initial_response = self.llm.generate_response(
                prompt,
                model="gemini-2.0-flash-lite",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Clean up response to ensure it's valid JSON
            initial_response = initial_response.strip()
            if initial_response.startswith("```json"):
                initial_response = initial_response.split("```json")[1]
            if initial_response.startswith("```"):
                initial_response = initial_response.split("```")[1]
            if initial_response.endswith("```"):
                initial_response = initial_response.rsplit("```", 1)[0]
            initial_response = initial_response.strip()
            
            try:
                # Parse initial analysis
                initial_result = json.loads(initial_response)
                
                # Prepare context for refinement
                context = {
                    "component_info": {
                        "classes": [{"name": c["name"], "method_count": len(c.get("methods", []))} for c in component_info.get("classes", [])],
                        "functions": [{"name": f["name"]} for f in component_info.get("functions", [])],
                        "imports": component_info.get("imports", [])
                    }
                }
                
                # Refine the analysis
                refined_result = self._refine_analysis(
                    "component responsibilities",
                    initial_result,
                    context
                )
                
                # Extract responsibilities from the refined result
                if isinstance(refined_result, dict) and "responsibilities" in refined_result:
                    for item in refined_result["responsibilities"]:
                        if isinstance(item, dict) and "responsibilities" in item:
                            # Ensure we're only adding strings to the set
                            for resp in item["responsibilities"]:
                                if isinstance(resp, str):
                                    responsibilities.add(resp)
            
            except json.JSONDecodeError as e:
                self.console.print(f"[yellow]Error parsing JSON content: {e}[/yellow]")
                return list(responsibilities)
            
        except Exception as e:
            self.console.print(f"[yellow]Error generating responsibilities: {e}[/yellow]")
        
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

    def _refine_analysis(self, analysis_type: str, initial_analysis: dict, context: dict) -> dict:
        """Refine initial analysis using the full flash model.
        
        Args:
            analysis_type: Type of analysis being refined
            initial_analysis: Initial analysis to refine
            context: Additional context for refinement
            
        Returns:
            Refined analysis as a dictionary
        """
        try:
            # Convert initial analysis to JSON string
            initial_json = json.dumps(initial_analysis, indent=2)
            
            prompt = f"""You are performing a refinement pass on an initial analysis. Your task is to validate, expand, and improve upon the initial analysis.

Analysis Type: {analysis_type}

Initial Analysis:
{initial_json}

Additional Context:
{json.dumps(context, indent=2)}

Requirements:
1. Validate all findings in the initial analysis
2. Identify any patterns or relationships not caught initially
3. Suggest improvements or missing aspects
4. Maintain the exact same JSON structure as the input

IMPORTANT: Your response must be ONLY a valid JSON object matching the structure of the initial analysis.
DO NOT include any other text, markdown, or explanations - just the raw JSON.

Refined Analysis:"""

            # Use flash model with strict JSON formatting
            response = self.llm.generate_response(
                prompt,
                model="gemini-2.0-flash",
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            try:
                # First try direct JSON parsing
                refined = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the response
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    try:
                        refined = json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from response: {response}")
                        return initial_analysis
                else:
                    logger.error(f"No JSON object found in response: {response}")
                    return initial_analysis

            # Validate refined analysis has same structure as initial
            if not all(key in refined for key in initial_analysis.keys()):
                logger.warning("Refined analysis missing some original keys, using initial analysis")
                return initial_analysis

            return refined

        except Exception as e:
            logger.error(f"Refinement failed: {str(e)}")
            return initial_analysis

    def _discover_modules(self, target_dir: str) -> dict:
        """Analyze all Python modules in the target directory to understand their purpose and relationships."""
        file_summaries = []
        total_size = 0
        consolidated_content = []
        
        # Walk through all Python files in the target directory
        for root, _, files in os.walk(target_dir):
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not content.strip():
                            continue
                            
                        # Get file size
                        total_size += len(content)
                        
                        # Extract key information
                        imports = []
                        classes = []
                        functions = []
                        docstring = ""
                        
                        try:
                            tree = ast.parse(content)
                            
                            # Get module docstring if it exists
                            if ast.get_docstring(tree):
                                docstring = ast.get_docstring(tree)
                                
                            # Extract imports, classes, and functions
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for name in node.names:
                                        imports.append(name.name)
                                elif isinstance(node, ast.ImportFrom):
                                    module = node.module or ''
                                    for name in node.names:
                                        imports.append(f"{module}.{name.name}")
                                elif isinstance(node, ast.ClassDef):
                                    classes.append({
                                        'name': node.name,
                                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                                        'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                                        'docstring': ast.get_docstring(node) or ''
                                    })
                                elif isinstance(node, ast.FunctionDef):
                                    functions.append({
                                        'name': node.name,
                                        'args': [arg.arg for arg in node.args.args],
                                        'docstring': ast.get_docstring(node) or ''
                                    })
                                    
                            # Add to consolidated content
                            consolidated_content.append(f"# File: {os.path.relpath(file_path, target_dir)}\n{content}\n")
                                
                        except SyntaxError:
                            logger.warning(f"Could not parse {file_path}")
                            continue
                            
                        # Create file summary with enhanced information
                        rel_path = os.path.relpath(file_path, target_dir)
                        summary = {
                            "file": rel_path,
                            "size": len(content),
                            "imports": imports,
                            "classes": classes,
                            "functions": functions,
                            "docstring": docstring[:200] if docstring else None,  # Limit docstring length
                            "directory": os.path.dirname(rel_path),
                            "complexity_indicators": {
                                "class_count": len(classes),
                                "function_count": len(functions),
                                "import_count": len(imports),
                                "loc": len(content.splitlines())
                            }
                        }
                        file_summaries.append(summary)
                        
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
                    continue

        # Create a more comprehensive analysis prompt
        analysis_prompt = f"""Analyze this Python codebase and provide a detailed architectural assessment.

File Structure Summary:
{json.dumps(file_summaries, indent=2)}

Full Codebase Context:
{''.join(consolidated_content)}

Provide a comprehensive JSON response with:
{{
    "repository_purpose": "A clear description of what this codebase does",
    "key_components": [
        {{
            "name": "Component name (e.g. file or module)",
            "purpose": "What this component does",
            "dependencies": ["List of key dependencies"],
            "architectural_role": "The component's role in the system architecture",
            "complexity_assessment": "Assessment of component complexity and quality"
        }}
    ],
    "architecture_patterns": [
        {{
            "pattern": "Name of the architectural pattern",
            "evidence": "Where and how this pattern is implemented",
            "benefits": "Benefits this pattern provides",
            "tradeoffs": "Tradeoffs or potential issues with this pattern"
        }}
    ],
    "dependency_analysis": {{
        "external_dependencies": ["List of external package dependencies"],
        "internal_dependencies": ["List of internal module dependencies"],
        "dependency_patterns": ["Observed dependency patterns or anti-patterns"]
    }},
    "architectural_metrics": {{
        "modularity": "Assessment of code modularity (High/Medium/Low)",
        "coupling": "Assessment of component coupling",
        "cohesion": "Assessment of component cohesion",
        "complexity": "Overall architectural complexity assessment"
    }},
    "validation": {{
        "issues": [
            {{
                "issue": "Description of the architectural issue",
                "severity": "High/Medium/Low",
                "impact": "Impact of the issue",
                "recommendation": "Suggested fix or improvement"
            }}
        ],
        "recommendations": [
            {{
                "area": "Area of improvement",
                "suggestion": "Specific suggestion",
                "rationale": "Why this improvement would help"
            }}
        ]
    }}
}}

Focus on identifying architectural patterns, assessing component relationships, and finding potential issues."""

        try:
            # Initial analysis with flash-lite
            initial_response = self.llm.generate_response(
                analysis_prompt,
                model="gemini-2.0-flash-lite",
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            try:
                initial_analysis = json.loads(initial_response)
                
                # Prepare enhanced context for refinement
                context = {
                    "file_summaries": file_summaries,
                    "total_files": len(file_summaries),
                    "total_size": total_size,
                    "file_types": list(set(f["file"].split(".")[-1] for f in file_summaries)),
                    "directory_structure": self._analyze_directory_structure(file_summaries),
                    "complexity_metrics": self._calculate_complexity_metrics(file_summaries)
                }
                
                # Refine the analysis
                refined_analysis = self._refine_analysis(
                    "repository structure",
                    initial_analysis,
                    context
                )
                
                # Log analysis diagnostics
                self._log_architectural_diagnostics(refined_analysis)
                
                logger.info("Successfully analyzed repository structure")
                return refined_analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse analysis response: {e}")
                return {
                    "repository_purpose": "Failed to analyze repository",
                    "key_components": [],
                    "dependencies": [],
                    "architecture_patterns": [],
                    "validation": {"issues": [], "recommendations": []}
                }
                
        except Exception as e:
            logger.error(f"Error during repository analysis: {e}")
            return {
                "repository_purpose": "Failed to analyze repository",
                "key_components": [],
                "dependencies": [],
                "architecture_patterns": [],
                "validation": {"issues": [], "recommendations": []}
            }

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
        """Extract key details from a consolidated function file."""
        content = path.read_text()
        return {
            "path": path,
            "name": path.stem.replace("consolidated_", ""),
            "content": content,
            "dependencies": self._find_dependencies(content),
            "function_type": self._classify_function(content),
        }

    def _classify_function(self, code: str) -> dict:
        """Use LLM to classify function purpose."""
        try:
            prompt = f"""Classify this Python function's purpose:
            {code}

            Output JSON with:
            - primary_category: "core", "research", "accounting", "llm", "utils", "pipeline"
            - secondary_category: specific module if applicable
            - functionality_summary: 1-2 sentence description
            """
            # Remove fallback_model from kwargs
            response = self.llm.generate_response(
                prompt,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            return json.loads(response)
        except Exception as e:
            self.console.print(f"[yellow]Error classifying function: {e}[/yellow]")
            return {
                "primary_category": "utils",
                "secondary_category": "unknown",
                "functionality_summary": "Could not analyze function"
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

    def _architectural_review(self, func_desc: str) -> dict:
        """Enhanced LLM analysis with stakeholder context."""
        try:
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
            - security_considerations: list of strings
            - data_sources: list of required data inputs
            """

            # Remove fallback_model from kwargs
            response = self.llm.generate_response(
                prompt,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000
            )
            return json.loads(response)
        except Exception as e:
            self.console.print(f"[yellow]Error in architectural review: {e}[/yellow]")
            return {
                "recommended_module": "utils",
                "required_dependencies": [],
                "architecture_rules": [],
                "security_considerations": [],
                "data_sources": []
            }

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
        """Reformat code using LLM."""
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
            # Remove model and fallback_model from kwargs
            return self.llm.generate_response(
                prompt,
                temperature=0.1,
                max_tokens=4000
            )
        except Exception as e:
            self.console.print(f"[yellow]⚠️ Reformating failed: {e}[/yellow]")
            return content  # Return original if reformat fails

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
            # Initial analysis with flash-lite
            initial_prompt = f"""Analyze and enhance this PRD:

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

            initial_response = self.llm.generate_response(
                initial_prompt,
                model="gemini-2.0-flash-lite",
                temperature=0.3
            )
            
            try:
                initial_result = json.loads(initial_response)
                
                # Prepare context for refinement
                context = {
                    "total_components": len(self.prd_data.get("components", {})),
                    "total_decisions": len(self.prd_data.get("decisions", {}).get("issues", [])),
                    "architecture_patterns": self.prd_data.get("decisions", {}).get("patterns", []),
                    "metadata": self.prd_data.get("metadata", {})
                }
                
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
                
                # Display convention issues
                if "convention_issues" in refined_result and refined_result["convention_issues"]:
                    self.console.print("\n[yellow]Convention Issues Found:[/yellow]")
                    for issue in refined_result["convention_issues"]:
                        self.console.print(f"  • {issue['issue']}")
                        self.console.print(f"    Fix: {issue['fix']}")
                
                    if self.console.input("\nAttempt automatic fixes? [y/n]: ").lower() == 'y':
                        self._apply_convention_fixes(refined_result["convention_issues"])
                else:
                    self.console.print("  ✅ No convention issues found")
                
                # Display improvement suggestions
                if "suggested_improvements" in refined_result and refined_result["suggested_improvements"]:
                    self.console.print("\n[bold]Suggested Improvements:[/bold]")
                    for suggestion in refined_result["suggested_improvements"]:
                        self.console.print(f"  • {suggestion}")
                    
            except json.JSONDecodeError:
                self.console.print("[yellow]Error parsing LLM response[/yellow]")
            
        except Exception as e:
            self.console.print(f"[red]Error during PRD finalization: {e}[/red]")
        
        # Save the PRD
        self._save_prd()

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
                model="gemini-2.0-flash-lite",
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
        """Generate an executive summary using LLM analysis of the PRD content."""
        try:
            prompt = f"""Generate an executive summary for this PRD:
{json.dumps(self.prd_data, indent=2)}

The summary should be concise (2-3 paragraphs) and cover:
1. Project purpose and scope
2. Key components and their roles
3. Major architectural decisions and changes needed

Return ONLY the summary text, no other text or formatting."""

            response = self.llm.generate_response(
                prompt,
                model="gemini-2.0-flash-lite",  # Use lite model for text generation
                temperature=0.3
            )
            
            if response:
                self.prd_data['executive_summary'] = response.strip()
                return True
            return False
            
        except Exception as e:
            self.console.print(f"[yellow]Error generating executive summary: {e}[/yellow]")
            return False

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

    def _generate_docs(self) -> None:
        """Create both YAML and Markdown versions of PRD following conventions.
        
        Conventions:
        - Both YAML and MD versions must be maintained
        - Files must be in docs directory within target directory
        - Use standardized naming format
        """
        # Get directory name for title
        dir_name = self.target_dir.name.replace("_", " ").title()
        
        # Save YAML version first
        self._save_prd()  # This saves to self.prd_path which is already properly configured
        
        # Generate Markdown version
        md_path = self.prd_path.with_suffix(".md")
        
        template = f"""# {dir_name} Product Requirements Document

## Executive Summary
{self.prd_data.get('executive_summary', 'No executive summary provided.')}

## Project Overview
- **Title:** {self.prd_data.get('title', 'Untitled')}
- **Description:** {self.prd_data.get('description', 'No description provided.')}

## Stakeholders
### Primary Stakeholders
{self._format_stakeholders(self.prd_data.get('stakeholders', {}).get('default', []))}

### Client Modules Stakeholders
{self._format_stakeholders(self.prd_data.get('stakeholders', {}).get('client_modules', []))}

### Legal & Compliance
{self._format_stakeholders(self.prd_data.get('stakeholders', {}).get('legal_compliance', []))}

## Market Assessment
- **Default Market:** {self.prd_data.get('market_assessment', {}).get('default', 'Not specified')}
- **Client-Facing Market:** {self.prd_data.get('market_assessment', {}).get('client_facing', 'Not specified')}

## Core Components
{self._format_components()}

## Architectural Decisions
{self._format_decisions()}

## Requirements
### Functional Requirements
{self._format_requirements(self.prd_data.get('requirements', {}).get('functional', []))}

### Technical Requirements
{self._format_requirements(self.prd_data.get('requirements', {}).get('technical', []))}

### Compliance Requirements
{self._format_requirements(self.prd_data.get('requirements', {}).get('compliance', []))}

## Project Timeline
| Phase | Duration (weeks) |
|-------|-----------------|
| Discovery | {self.prd_data.get('timelines', {}).get('discovery', 'N/A')} |
| Development | {self.prd_data.get('timelines', {}).get('development', 'N/A')} |
| Testing | {self.prd_data.get('timelines', {}).get('testing', 'N/A')} |
| Deployment | {self.prd_data.get('timelines', {}).get('deployment', 'N/A')} |

## Assumptions & Constraints
{self._format_list(self.prd_data.get('assumptions', []))}

## Evaluation Metrics
{self._format_list(self.prd_data.get('evaluation_metrics', []))}

## Version History
{self._format_version_history()}

---
*This document is automatically generated and maintained by the PRD Builder. Both YAML and Markdown versions are tracked in dewey.yaml.*
"""

        md_path.write_text(template)
        self.console.print(f"[green]Generated PRD files:[/green]")
        self.console.print(f"  • YAML: {self.prd_path}")
        self.console.print(f"  • Markdown: {md_path}")

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
