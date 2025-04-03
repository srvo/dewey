"""Code documentation analysis and generation agent using smolagents."""

import ast
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog
from smolagents import Tool

from .base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class DocstringAgent(BaseAgent):
    """Agent for analyzing and generating code documentation.

    Features:
        - Docstring analysis and improvement
        - Style compliance checking
        - Context-aware documentation
        - Dependency documentation
        - Complexity analysis
    """

    def __init__(self):
        """Initializes the DocstringAgent."""
        super().__init__(task_type="docstring")
        self.add_tools(
            [
                Tool.from_function(
                    self.extract_code_context,
                    description="Extracts context from code using AST analysis.",
                ),
                Tool.from_function(
                    self._calculate_complexity,
                    description="Calculates cyclomatic complexity of an AST node.",
                ),
            ]
        )

    def extract_code_context(self, code: str) -> List[Dict[str, Any]]:
        """Extracts context from code using AST analysis.

        Args:
            code (str): Source code to analyze.

        Returns:
            List[Dict[str, Any]]: A list of code contexts.

        """
        contexts = []
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                context = {
                    "name": getattr(node, "name", "<module>"),
                    "type": type(node).__name__.lower().replace("def", ""),
                    "code": ast.get_source_segment(code, node),
                    "docstring": ast.get_docstring(node),
                    "complexity": self._calculate_complexity(node),
                }
                contexts.append(context)

        return contexts

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculates cyclomatic complexity of an AST node.

        Args:
            node (ast.AST): The AST node to analyze.

        Returns:
            int: The cyclomatic complexity.

        """
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyzes a file and improves its documentation.

        Args:
            file_path (Path): The path to the file to analyze.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the analysis results, or None if an error occurs.

        """
        try:
            code = file_path.read_text()
            contexts = self.extract_code_context(code)

            # Construct a prompt for analyzing the code and improving its documentation
            prompt = f"""
            Analyze the following code and improve its documentation:
            {code}

            Code Contexts:
            {contexts}
            """

            # Run the agent with the prompt
            result = self.run(prompt)
            return {"result": result, "contexts": contexts}

        except Exception as e:
            self.logger.error(f"Error analyzing file: {e}")
            return None
