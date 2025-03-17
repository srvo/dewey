"""Code documentation analysis and generation agent."""

from typing import List, Dict, Any, Optional
import ast
from pathlib import Path
from pydantic import BaseModel, Field
import structlog

from ..base import SyzygyAgent

logger = structlog.get_logger(__name__)


class CodeContext(BaseModel):
    """Context about a code element."""

    name: str
    type: str  # class, function, module
    code: str
    docstring: Optional[str]
    parent: Optional[str]
    dependencies: List[str] = Field(default_factory=list)
    complexity: Optional[int]


class DocStringAnalysis(BaseModel):
    """Analysis of existing docstrings."""

    completeness: float
    clarity: float
    style_compliance: float
    issues: List[str]
    suggestions: List[str]


class DocStringAgent(SyzygyAgent):
    """Agent for analyzing and generating code documentation.

    Features:
    - Docstring analysis and improvement
    - Style compliance checking
    - Context-aware documentation
    - Dependency documentation
    - Complexity analysis
    """

    def __init__(self):
        """Initialize the DocString agent."""
        super().__init__(
            task_type="code_documentation",
            model="qwen-coder-32b",  # Use code-specialized model
        )

    def extract_code_context(self, code: str) -> List[CodeContext]:
        """Extract context from code using AST analysis.

        Args:
            code: Source code to analyze

        Returns:
            List of code contexts
        """
        contexts = []
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                context = CodeContext(
                    name=getattr(node, "name", "<module>"),
                    type=type(node).__name__.lower().replace("def", ""),
                    code=ast.get_source_segment(code, node),
                    docstring=ast.get_docstring(node),
                    parent=getattr(node.parent, "name", None)
                    if hasattr(node, "parent")
                    else None,
                    complexity=self._calculate_complexity(node),
                )
                contexts.append(context)

        return contexts

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST node."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    async def analyze_docstrings(
        self, contexts: List[CodeContext]
    ) -> Dict[str, DocStringAnalysis]:
        """Analyze existing docstrings for quality and completeness.

        Args:
            contexts: List of code contexts to analyze

        Returns:
            Dictionary mapping names to docstring analysis
        """
        analyses = {}

        for context in contexts:
            result = await self.run(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Analyze this docstring for quality and completeness:

Code Type: {context.type}
Name: {context.name}
Docstring: {context.docstring or "None"}
Code:
{context.code}

Consider:
1. Completeness (args, returns, raises)
2. Clarity and readability
3. Style compliance (PEP 257)
4. Technical accuracy
5. Context and examples""",
                    }
                ],
                model="qwen-coder-32b",
                metadata={"context": context.dict()},
            )

            analyses[context.name] = DocStringAnalysis(**result)

        return analyses

    async def generate_docstring(self, context: CodeContext) -> str:
        """Generate a high-quality docstring for a code element.

        Args:
            context: Context about the code element

        Returns:
            Generated docstring
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate a comprehensive docstring for this code:

Type: {context.type}
Name: {context.name}
Code:
{context.code}

Requirements:
1. Follow PEP 257 style
2. Include all parameters
3. Document return values
4. Note exceptions
5. Provide clear description
6. Add examples if helpful""",
                }
            ],
            model="qwen-coder-32b",
            metadata={
                "complexity": context.complexity,
                "has_existing": bool(context.docstring),
            },
        )

        return result["docstring"]

    async def improve_docstring(
        self, context: CodeContext, analysis: DocStringAnalysis
    ) -> str:
        """Improve an existing docstring based on analysis.

        Args:
            context: Context about the code element
            analysis: Analysis of current docstring

        Returns:
            Improved docstring
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Improve this docstring based on analysis:

Current Docstring:
{context.docstring}

Analysis:
- Completeness: {analysis.completeness}
- Clarity: {analysis.clarity}
- Style Compliance: {analysis.style_compliance}
- Issues: {", ".join(analysis.issues)}

Code:
{context.code}

Requirements:
1. Address all identified issues
2. Maintain existing correct information
3. Follow PEP 257 style
4. Improve clarity and completeness""",
                }
            ],
            model="qwen-coder-32b",
            metadata={
                "issues": len(analysis.issues),
                "current_scores": analysis.dict(),
            },
        )

        return result["improved_docstring"]

    async def document_file(self, file_path: Path) -> Dict[str, str]:
        """Generate or improve docstrings for an entire file.

        Args:
            file_path: Path to the file to document

        Returns:
            Dictionary mapping names to new/improved docstrings
        """
        with open(file_path) as f:
            code = f.read()

        contexts = self.extract_code_context(code)
        analyses = await self.analyze_docstrings(contexts)

        docstrings = {}
        for context in contexts:
            if not context.docstring:
                docstrings[context.name] = await self.generate_docstring(context)
            elif analyses[context.name].completeness < 0.8:
                docstrings[context.name] = await self.improve_docstring(
                    context, analyses[context.name]
                )

        return docstrings
