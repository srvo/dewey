# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Code documentation analysis and generation agent."""
from pathlib import Path
from .docstring_agent import DocstringAgent  # Import the new agent

async def document_file(file_path: Path) -> dict[str, str]:
    """Generate or improve docstrings for an entire file using the new DocstringAgent."""
    agent = DocstringAgent()
    return await agent.analyze_file(file_path)
