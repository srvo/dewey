#!/usr/bin/env python
"""Generate SEARCH/REPLACE blocks with TODOs for legacy files"""

import subprocess
from pathlib import Path

def get_legacy_files():
    """Get list of legacy files from code_uniqueness_analyzer.py"""
    result = subprocess.run(
        ["python", "src/dewey/scripts/code_uniqueness_analyzer.py"],
        capture_output=True, text=True
    )
    return [
        line.strip("- ").strip() 
        for line in result.stdout.splitlines() 
        if line.startswith("- ")
    ]

def generate_todo_comment(file_path: str) -> str:
    """Use aider to generate a TODO comment for the file"""
    prompt = f"""Create a TODO comment for this legacy file following CONVENTIONS.md.
Use this format at the TOP of the file:

# TODO: [Priority] [Category] - [Brief description]
# - Required: [Mandatory changes]
# - Optional: [Recommended improvements]
# - Reference: [Relevant convention section]

Categories: Config, ErrorHandling, TypeHints, Structure, LLM, Testing, Docs, Security
Priorities: Critical, High, Medium, Low
Max 5 bullet points. Include blank line after comment."""

    cmd = [
        "aider", "--no-show-model-warnings",
        "--model", "gemini/gemini-0.5-flash",
        "-p", prompt, file_path
    ]
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return extract_first_comment(result.stdout)
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
    return ""

def extract_first_comment(output: str) -> str:
    """Extract the first comment block from aider's output"""
    lines = []
    in_comment = False
    for line in output.splitlines():
        if line.strip().startswith("# TODO:"):
            in_comment = True
            lines.append(line)
        elif in_comment:
            if line.startswith("#"):
                lines.append(line)
            else:
                break
    return "\n".join(lines)

def generate_search_replace(file_path: str, todo: str) -> str:
    """Generate the SEARCH/REPLACE block"""
    if not todo:
        return ""
    
    try:
        with open(file_path, "r") as f:
            original = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return ""
    
    new_content = f"{todo.rstrip()}\n\n{original}"
    
{new_content}
