#!/usr/bin/env python3

"""Script to find Python files that need to be updated to use BaseScript."""

import os
from pathlib import Path
from typing import Set
import libcst as cst
import libcst.matchers as m
from libcst.metadata import MetadataWrapper

def find_python_files(directory: Path) -> Set[Path]:
    """Find all Python files in the directory."""
    python_files = set()
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.add(Path(root) / file)
    return python_files

def analyze_file(file_path: Path) -> bool:
    """Analyze a Python file to determine if it needs BaseScript updates."""
    try:
        with open(file_path) as f:
            content = f.read()

        module = cst.parse_module(content)
        wrapper = MetadataWrapper(module)

        # Check for BaseScript import
        has_base_script_import = False
        for node in wrapper.module.body:
            if m.matches(node, m.Import() | m.ImportFrom()):
                if "BaseScript" in str(node):
                    has_base_script_import = True
                    break

        # Check for BaseScript inheritance
        has_base_script_inheritance = False
        class_finder = ClassFinder()
        wrapper.visit(class_finder)
        has_base_script_inheritance = any(
            'BaseScript' in str(bases) for _, bases in class_finder.classes
        )

        # Check for direct logging usage
        has_direct_logging = False
        logging_finder = LoggingFinder()
        wrapper.visit(logging_finder)
        has_direct_logging = bool(logging_finder.logging_statements)

        # Check for direct path usage
        has_direct_path = False
        path_finder = PathFinder()
        wrapper.visit(path_finder)
        has_direct_path = bool(path_finder.path_usages)

        # File needs update if any of these conditions are true
        return (
            not has_base_script_import or
            not has_base_script_inheritance or
            has_direct_logging or
            has_direct_path
        )

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return True  # Include file if we can't analyze it

class ClassFinder(cst.CSTVisitor):
    """Find classes and their inheritance."""

    def __init__(self):
        """Function __init__."""
        self.classes = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Function visit_ClassDef."""
        self.classes.append((node.name.value, node.bases))

class LoggingFinder(cst.CSTVisitor):
    """Find direct logging usage."""

    def __init__(self):
        """Function __init__."""
        self.logging_statements = []

    def visit_Call(self, node: cst.Call) -> None:
        """Function visit_Call."""
        if isinstance(node.func, cst.Attribute):
            if node.func.attr.value in ['debug', 'info', 'warning', 'error', 'critical']:
                self.logging_statements.append(node)

class PathFinder(cst.CSTVisitor):
    """Find direct path usage."""

    def __init__(self):
        """Function __init__."""
        self.path_usages = []

    def visit_Call(self, node: cst.Call) -> None:
        """Function visit_Call."""
        if isinstance(node.func, (cst.Name, cst.Attribute)):
            func_name = str(node.func)
            if any(name in func_name for name in ['os.path', 'Path', 'pathlib']):
                self.path_usages.append(node)

def main():
"""Execute main functions to find non-compliant files."""
    # Get the src directory
    src_dir = Path('src')
    if not src_dir.exists():
        print("Error: src directory not found")
        return

    # Find all Python files
    python_files = find_python_files(src_dir)
    print(f"Found {len(python_files)} Python files")

    # Analyze each file
    non_compliant_files = []
    for file_path in sorted(python_files):
        if analyze_file(file_path):
            non_compliant_files.append(str(file_path))
            print(f"Non-compliant: {file_path}")

    # Write results to output file
    output_file = Path('output_dir') / 'base_script.txt'
    with open(output_file, 'w') as f:
        for file_path in non_compliant_files:
            f.write(f"{file_path}\n")

    print(f"\nFound {len(non_compliant_files)} non-compliant files")
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()
