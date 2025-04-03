#!/usr/bin/env python3
"""Generate an index of Python classes in the repository.

This script scans all Python files in the repository and creates
an index file mapping class names to their file locations.
This makes class lookups much faster for other tools.

Usage:
  python index_classes.py
"""

import os
import re
import json
import time
from typing import Dict, List, Tuple


def colorize(text: str, color_code: str) -> str:
    """Add color to text."""
    return f"\033[{color_code}m{text}\033[0m"


def find_python_files(root_dir: str = ".") -> List[str]:
    """Find all Python files in the repository.
    
    Args:
        root_dir: Root directory to start the search
        
    Returns:
        List of Python file paths
    """
    python_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip directories that typically don't contain source code
        if (any(part.startswith('.') for part in dirpath.split(os.sep)) or 
            any(excluded in dirpath for excluded in [
                'venv', 'env', '__pycache__', 'node_modules', 'build', 'dist'
            ])):
            continue
            
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(os.path.join(dirpath, filename))
    
    return python_files


def extract_classes_from_file(file_path: str) -> List[Tuple[str, str]]:
    """Extract class names from a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of tuples (class_name, file_path)
    """
    classes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regular expression to find class definitions
        class_pattern = re.compile(r'class\s+(\w+)\s*(?:\(.*?\))?:')
        matches = class_pattern.finditer(content)
        
        for match in matches:
            class_name = match.group(1)
            classes.append((class_name, file_path))
            
    except Exception as e:
        print(colorize(f"Error processing {file_path}: {e}", "1;31"))
    
    return classes


def build_class_index() -> Dict[str, str]:
    """Build an index mapping class names to file paths.
    
    Returns:
        Dictionary mapping class names to file paths
    """
    start_time = time.time()
    print(colorize("Building class index...", "1;36"))
    
    # Find all Python files
    python_files = find_python_files()
    print(colorize(f"Found {len(python_files)} Python files", "1;33"))
    
    # Build the index
    class_index = {}
    total_classes = 0
    
    for i, file_path in enumerate(python_files, 1):
        # Show progress every 100 files
        if i % 100 == 0 or i == len(python_files):
            print(colorize(f"Processing files: {i}/{len(python_files)}", "1;33"))
            
        classes = extract_classes_from_file(file_path)
        for class_name, path in classes:
            class_index[class_name] = path
            total_classes += 1
    
    elapsed_time = time.time() - start_time
    print(colorize(f"Found {total_classes} classes in {elapsed_time:.2f} seconds", "1;32"))
    
    return class_index


def save_index_to_file(class_index: Dict[str, str], output_file: str = "class_index.json") -> None:
    """Save the class index to a JSON file.
    
    Args:
        class_index: Dictionary mapping class names to file paths
        output_file: Path to the output file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(class_index, f, indent=2)
    
    print(colorize(f"Class index saved to {output_file}", "1;32"))
    print(colorize(f"Index contains {len(class_index)} classes", "1;32"))


def main() -> None:
    """Main function."""
    print(colorize("====== CLASS INDEXER ======", "1;36"))
    print(colorize("Building an index of all Python classes in the repository", "1;37"))
    
    class_index = build_class_index()
    save_index_to_file(class_index)
    
    print(colorize("\nDone!", "1;32"))
    print(colorize("You can now use this index in other scripts for faster class lookups", "1;37"))


if __name__ == "__main__":
    main() 