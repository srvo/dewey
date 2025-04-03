#!/usr/bin/env python3
"""
Fix Common Issues - Script to automatically fix common flake8 issues that black doesn't handle.
"""

import ast
import logging
import re
import sys
from pathlib import Path
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fix_common_issues")


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to collect imports."""

    def __init__(self):
        self.imports = {}  # name -> module or alias
        self.from_imports = {}  # (module, name) -> alias
        self.star_imports = []  # modules with * imports

    def visit_Import(self, node):
        for name in node.names:
            self.imports[name.asname or name.name] = name.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module is None:  # relative import
            return

        if any(name.name == "*" for name in node.names):
            self.star_imports.append(node.module)
        else:
            for name in node.names:
                self.from_imports[(node.module, name.name)] = name.asname or name.name
        self.generic_visit(node)


class NameVisitor(ast.NodeVisitor):
    """AST visitor to collect name references."""

    def __init__(self):
        self.used_names = set()
        self.defined_names = set()
        self.used_attributes = set()  # For "a.b" store "a"

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            self.used_attributes.add(node.value.id)
        self.generic_visit(node)


def fix_unused_imports(content: str) -> str:
    """Fix unused imports."""
    try:
        tree = ast.parse(content)

        # Find all imports
        import_visitor = ImportVisitor()
        import_visitor.visit(tree)

        # Find all used names
        name_visitor = NameVisitor()
        name_visitor.visit(tree)

        # Combine all used identifiers
        used_names = name_visitor.used_names.union(name_visitor.used_attributes)

        # Find unused imports
        unused_imports = []
        for name in used_names:
            if name not in used_names and name not in name_visitor.defined_names:
                unused_imports.append(name)

        unused_from_imports = []
        for (module, name), alias in import_visitor.from_imports.items():
            if alias not in used_names and alias not in name_visitor.defined_names:
                unused_from_imports.append((module, name, alias))

        # If there's a star import, we can't safely remove other imports
        if import_visitor.star_imports:
            return content

        # Remove unused imports
        lines = content.split("\n")
        result_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for import statements
            import_match = re.match(r"^\s*import\s+(.*)", line)
            from_import_match = re.match(r"^\s*from\s+(\S+)\s+import\s+(.*)", line)

            if import_match:
                # Handle multi-line imports
                full_line = line
                while full_line.strip().endswith("\\") or full_line.strip().endswith(
                    ","
                ):
                    i += 1
                    if i >= len(lines):
                        break
                    full_line += "\n" + lines[i]

                # Parse imports
                parts = []
                for part in re.split(r",\s*", import_match.group(1)):
                    if " as " in part:
                        module, alias = part.split(" as ")
                        if alias.strip() not in unused_imports:
                            parts.append(part)
                    else:
                        if part.strip() not in unused_imports:
                            parts.append(part)

                # Reconstruct the line if there are remaining imports
                if parts:
                    new_line = "import " + ", ".join(parts)
                    result_lines.append(new_line)
            elif from_import_match:
                module = from_import_match.group(1)
                imports = from_import_match.group(2)

                # Handle multi-line imports
                full_line = line
                while full_line.strip().endswith("\\") or full_line.strip().endswith(
                    ","
                ):
                    i += 1
                    if i >= len(lines):
                        break
                    full_line += "\n" + lines[i]

                # Parse imports
                parts = []
                for part in re.split(r",\s*", imports):
                    if " as " in part:
                        name, alias = part.split(" as ")
                        if (
                            module,
                            name.strip(),
                            alias.strip(),
                        ) not in unused_from_imports:
                            parts.append(part)
                    else:
                        if (
                            module,
                            part.strip(),
                            part.strip(),
                        ) not in unused_from_imports:
                            parts.append(part)

                # Reconstruct the line if there are remaining imports
                if parts:
                    new_line = f"from {module} import " + ", ".join(parts)
                    result_lines.append(new_line)
            else:
                result_lines.append(line)

            i += 1

        return "\n".join(result_lines)
    except SyntaxError:
        # If there's a syntax error, just return the original content
        return content


def fix_bare_except(content: str) -> str:
"""Fix bare except statements by converting them to except Exception:."""
    pattern = r"except\s*:"
    return re.sub(pattern, "except Exception:", content)


def fix_missing_docstrings(content: str) -> str:
"""
    Add basic docstrings to functions and classes that are missing them.
    Note: This is a simple implementation and won't handle all cases perfectly.

"""
    try:
        tree = ast.parse(content)
        missing_docstrings = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    missing_docstrings.append(
                        (node.lineno, node.name, isinstance(node, ast.ClassDef))
                    )

        if not missing_docstrings:
            return content

        lines = content.split("\n")
        result_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            result_lines.append(line)

            for lineno, name, is_class in missing_docstrings:
                if i + 1 == lineno:
                    indent = len(line) - len(line.lstrip())
                    docstring_indent = " " * (indent + 4)
                    if is_class:
                        docstring = f'{docstring_indent}"""Class {name}."""'
                    else:
                        docstring = f'{docstring_indent}"""Function {name}."""'
                    result_lines.append(docstring)

            i += 1

        return "\n".join(result_lines)
    except SyntaxError:
        # If there's a syntax error, just return the original content
        return content


def fix_mutable_defaults(content: str) -> str:
    """Fix mutable default arguments in function definitions."""
    pattern = r"def\s+(\w+)\s*\((.*?)\)\s*:"

    def replace_mutable_defaults(match):
        func_name = match.group(1)
        params = match.group(2)

        # Replace mutable defaults with None and add code to handle them
        new_params = []
        replacements = []

        for param in re.split(r",\s*", params):
            if "=" in param and any(
                m in param for m in ("[]", "{}", "list()", "dict()", "set()")
            ):
                param_name, default = param.split("=", 1)
                param_name = param_name.strip()
                default = default.strip()
                new_params.append(f"{param_name}=None")
                replacements.append((param_name, default))
            else:
                new_params.append(param)

        if not replacements:
            return match.group(0)

        result = f"def {func_name}({', '.join(new_params)}):"

        # Find the indentation of the function body
        lines = content[match.end() :].split("\n")
        if not lines:
            return match.group(0)

        # Find first non-empty line to determine indentation
        body_indent = ""
        for line in lines:
            if line.strip():
                body_indent = line[: len(line) - len(line.lstrip())]
                break

        # Add the replacement code
        for param_name, default in replacements:
            result += f"\n{body_indent}if {param_name} is None:\n{body_indent}    {param_name} = {default}"

        return result

    return re.sub(pattern, replace_mutable_defaults, content, flags=re.DOTALL)


def fix_file(file_path: Path, dry_run: bool = False) -> dict:
    """Apply all fixes to a file."""
    try:
        with open(file_path) as f:
            content = f.read()

        original_content = content
        changes = []

        # Apply fixes
        new_content = fix_unused_imports(content)
        if new_content != content:
            changes.append("Removed unused imports")
            content = new_content

        new_content = fix_bare_except(content)
        if new_content != content:
            changes.append("Fixed bare except statements")
            content = new_content

        new_content = fix_missing_docstrings(content)
        if new_content != content:
            changes.append("Added missing docstrings")
            content = new_content

        new_content = fix_mutable_defaults(content)
        if new_content != content:
            changes.append("Fixed mutable default arguments")
            content = new_content

        if not dry_run and changes and content != original_content:
            with open(file_path, "w") as f:
                f.write(content)

        return {
            "file": file_path,
            "changes": changes,
            "modified": bool(changes),
        }
    except Exception as e:
        logger.error(f"Error fixing {file_path}: {e}")
        return {
            "file": file_path,
            "changes": [],
            "modified": False,
            "error": str(e),
        }


def main():
"""Execute main functions to run the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix common flake8 issues")
    parser.add_argument(
        "--dir", "-d", required=True, help="File or directory to process"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually change files"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    path = Path(args.dir)
    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        sys.exit(1)

    python_files = []
    if path.is_file() and path.suffix == ".py":
        python_files = [path]
        logger.info(f"Processing single Python file: {path}")
    else:
        if not path.is_dir():
            logger.error(f"Path is not a directory or Python file: {path}")
            sys.exit(1)
        python_files = list(path.glob("**/*.py"))
        logger.info(f"Found {len(python_files)} Python files in {path}")

    results = []
    for file_path in python_files:
        logger.info(f"Processing {file_path}")
        result = fix_file(file_path, args.dry_run)
        results.append(result)
        if args.verbose and result["changes"]:
            for change in result["changes"]:
                logger.info(f"  {change}")

    # Summary
    modified_count = sum(1 for r in results if r["modified"])
    error_count = sum(1 for r in results if "error" in r)

    print("\n" + "=" * 70)
    print(f"FIX COMMON ISSUES SUMMARY FOR {path}")
    print("=" * 70)
    print(f"Total Python files processed: {len(python_files)}")
    print(f"Files modified: {modified_count}")
    print(f"Files with errors: {error_count}")

    if args.verbose:
        print("\nModified files:")
        for r in results:
            if r["modified"]:
                print(f"  {r['file']}")
                for change in r["changes"]:
                    print(f"    - {change}")

    if error_count > 0:
        print("\nFiles with errors:")
        for r in results:
            if "error" in r:
                print(f"  {r['file']}: {r['error']}")

    print("=" * 70)


if __name__ == "__main__":
    main()
