#!/usr/bin/env python
"""Pre-commit hook to check if abstract methods are properly implemented.

This script verifies that classes inheriting from certain base classes
implement their required abstract methods. Specifically:
- Classes inheriting from BaseScript must implement 'execute'
- Classes inheriting from BookkeepingScript must implement 'run'
"""

import argparse
import ast
import sys
from typing import List, Dict, Set, Tuple


class AbstractMethodVisitor(ast.NodeVisitor):
    """AST visitor to find classes and check for abstract method implementations."""

    def __init__(self):
        self.classes: Dict[str, Set[str]] = {}  # class_name -> set of method names
        self.base_classes: Dict[
            str, Set[str]
        ] = {}  # class_name -> set of base class names
        self.errors: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and store information about methods and base classes."""
        class_name = node.name
        self.classes[class_name] = set()
        self.base_classes[class_name] = set()

        # Record base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.base_classes[class_name].add(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle cases like module.BaseClass
                if isinstance(base.value, ast.Name):
                    self.base_classes[class_name].add(base.attr)

        # Record methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.classes[class_name].add(item.name)

        # Continue visiting child nodes
        self.generic_visit(node)


def check_file(filename: str) -> List[str]:
    """Check a Python file for abstract method implementation requirements."""
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [f"Syntax error in {filename}: {e}"]

    visitor = AbstractMethodVisitor()
    visitor.visit(tree)

    errors = []

    # Check for abstract method implementations
    for class_name, base_classes in visitor.base_classes.items():
        methods = visitor.classes.get(class_name, set())

        # BaseScript requires 'execute'
        if "BaseScript" in base_classes and "execute" not in methods:
            errors.append(
                f"Class '{class_name}' inherits from 'BaseScript' but doesn't implement the required 'execute' method"
            )

        # BookkeepingScript requires 'run'
        if "BookkeepingScript" in base_classes and "run" not in methods:
            errors.append(
                f"Class '{class_name}' inherits from 'BookkeepingScript' but doesn't implement the required 'run' method"
            )

    return errors


def main():
    """Parse arguments and run checks on specified files."""
    parser = argparse.ArgumentParser(
        description="Check if classes implement required abstract methods"
    )
    parser.add_argument("filenames", nargs="+", help="Files to check")
    args = parser.parse_args()

    all_errors = []
    for filename in args.filenames:
        if filename.endswith(".py"):
            errors = check_file(filename)
            all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
