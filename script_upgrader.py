#!/usr/bin/env python3
"""
Script Upgrader

This script processes the repomix-output.xml file, identifies script content,
and upgrades scripts to use BaseScript while preserving their functionality.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging

# Add aider imports
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput

# Configuration
REPO_ROOT = Path("/Users/srvo/dewey")
REPOMIX_FILE = REPO_ROOT / "repomix-output.xml"
SRC_DIR = REPO_ROOT / "src"
CONVENTIONS_FILE = REPO_ROOT / "CONVENTIONS.md"
BASESCRIPT_IMPORT = "from dewey.core.base_script import BaseScript"
BASESCRIPT_CLASS_PATTERN = r"class\s+(\w+)(?:\(.*?\))?\s*:"
BASESCRIPT_CLASS_REPLACEMENT = r"class \1(BaseScript):"
LOG_FILE = REPO_ROOT / "logs" / "script_upgrader.log"

def setup_logging():
    """Set up logging to both console and file."""
    log_dir = REPO_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("script_upgrader")

logger = setup_logging()

def parse_repomix_xml(xml_path: Path) -> Dict[str, str]:
    """
    Parse the repomix-output.xml file to extract script content.
    
    Args:
        xml_path: Path to the repomix-output.xml file
        
    Returns:
        Dictionary mapping file paths to their content
    """
    logger.info(f"Parsing {xml_path}")
    
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract Python files using regex
        script_contents = {}
        file_pattern = r'<file path="(.*?\.py)">(.*?)</file>'
        matches = re.finditer(file_pattern, content, re.DOTALL)
        
        for match in matches:
            path = match.group(1)
            if not path.endswith(".py"):
                continue
                
            script_content = match.group(2).strip()
            if script_content:
                # Skip files that are already upgraded
                if "from dewey.core.base_script import BaseScript" in script_content and len(script_content.strip().split('\n')) <= 3:
                    logger.debug(f"Skipping already upgraded script: {path}")
                    continue
                
                script_contents[path] = script_content
                logger.debug(f"Found script: {path}")
        
        logger.info(f"Found {len(script_contents)} Python scripts in XML")
        return script_contents
        
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        return {}

def is_script_using_basescript(content: str) -> bool:
    """
    Check if a script is already using BaseScript.
    
    Args:
        content: Script content
        
    Returns:
        True if the script already uses BaseScript
    """
    return (BASESCRIPT_IMPORT in content and 
            re.search(r"class\s+\w+\(BaseScript\)", content) is not None)

def get_existing_script_path(script_name: str) -> Optional[Path]:
    """
    Find the existing script in the repo.
    
    Args:
        script_name: Script filename
        
    Returns:
        Path to the existing script, or None if not found
    """
    result = list(SRC_DIR.rglob(script_name))
    return result[0] if result else None

def get_script_module(script_path: Path) -> Optional[str]:
    """
    Determine the Python module path for a script.
    
    Args:
        script_path: Path to the script
        
    Returns:
        Module path (e.g., dewey.core.utils)
    """
    try:
        rel_path = script_path.relative_to(SRC_DIR)
        parts = list(rel_path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]  # Remove .py extension
        return ".".join(parts)
    except ValueError:
        return None

def upgrade_script_content(
    original_content: str, 
    script_name: str, 
    existing_path: Optional[Path] = None,
    skip_aider: bool = False,
    model: str = "",
    return_method: bool = False
) -> Union[str, Tuple[str, str]]:
    """
    Upgrade script content to use BaseScript using aider.
    
    Args:
        original_content: Original script content
        script_name: Script filename
        existing_path: Path to existing script in repo
        skip_aider: Skip using aider and use direct method
        model: Model name to use with aider
        return_method: Whether to return the method used (aider or direct)
        
    Returns:
        Upgraded script content or tuple of (content, method)
    """
    if is_script_using_basescript(original_content):
        logger.info(f"{script_name} already uses BaseScript")
        if return_method:
            return original_content, "none"
        return original_content
    
    # Determine module path if existing script found
    config_section = "custom"
    if existing_path:
        module_path = get_script_module(existing_path)
        if module_path:
            parts = module_path.split(".")
            if len(parts) > 2:
                config_section = parts[2]  # Use the module name as config section
    
    # Try using aider CLI first, fallback to direct method if that fails
    if not skip_aider:
        try:
            logger.info(f"Attempting to upgrade {script_name} using aider CLI")
            upgraded_content = upgrade_with_aider_cli(original_content, config_section, model)
            
            # Verify the upgrade was successful
            if is_script_using_basescript(upgraded_content):
                logger.info(f"Successfully upgraded {script_name} using aider CLI")
                if return_method:
                    return upgraded_content, "aider"
                return upgraded_content
            else:
                logger.warning(f"Aider upgrade didn't include BaseScript for {script_name}")
        except Exception as e:
            logger.error(f"Error using aider CLI: {e}")
    else:
        logger.info(f"Skipping aider integration as requested")
    
    # Fallback to direct method
    logger.info(f"Using direct upgrade method for {script_name}")
    upgraded_content = fallback_upgrade(original_content, config_section)
    
    if return_method:
        return upgraded_content, "direct"
    return upgraded_content

def upgrade_with_aider_cli(original_content: str, config_section: str, model: str = "") -> str:
    """
    Upgrade script content using aider command line tool.
    
    Args:
        original_content: Original script content
        config_section: Configuration section name
        model: Model name to use with aider
        
    Returns:
        Upgraded script content
    """
    # Create a temporary directory to work in
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # Create a file with the original content
        script_path = temp_dir_path / "script.py"
        with open(script_path, "w") as f:
            f.write(original_content)
        
        # Copy conventions file if it exists
        conventions_dest = None
        if CONVENTIONS_FILE.exists():
            conventions_dest = temp_dir_path / "CONVENTIONS.md"
            with open(CONVENTIONS_FILE, "r") as src, open(conventions_dest, "w") as dest:
                dest.write(src.read())
        
        # Create a file with the prompt
        prompt_file = temp_dir_path / "prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(f"""
Upgrade this script to use BaseScript with the following requirements:
1. Add import: {BASESCRIPT_IMPORT}
2. Make the main class inherit from BaseScript
3. Call super().__init__(config_section='{config_section}') in __init__
4. Ensure all functionality is preserved
5. Use self.logger instead of direct logger usage
6. Use self.config for configuration
7. Follow dewey project conventions for BaseScript usage
8. Maintain consistent indentation (4 spaces)

Return the complete upgraded script.
""")
        
        # Run aider CLI
        files_to_include = [str(script_path)]
        if conventions_dest:
            files_to_include.append(str(conventions_dest))
            
        cmd = [
            "aider", 
            "--yes",            # Auto-confirm all prompts
            "--no-git",         # Don't use git
            "--message-file", str(prompt_file),
        ]
        
        # Add model if specified
        if model:
            cmd.extend(["--model", model])
            
        # Add files to include
        cmd.extend(files_to_include)
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=temp_dir_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Aider command failed: {result.stderr}")
            raise Exception(f"Aider command failed with code {result.returncode}")
        
        # Read the modified file
        with open(script_path, "r") as f:
            upgraded_content = f.read()
        
        logger.debug(f"Aider output: {result.stdout}")
            
        # Fix any indentation issues
        return fix_indentation(upgraded_content)

def fix_indentation(content: str) -> str:
    """
    Fix common indentation issues in the upgraded script.
    
    Args:
        content: The script content
        
    Returns:
        Content with fixed indentation
    """
    lines = content.split('\n')
    fixed_lines = []
    in_init = False
    init_indent = ""
    
    for i, line in enumerate(lines):
        # Track when we enter __init__ method
        if re.search(r"def __init__\s*\(", line):
            in_init = True
            init_indent = re.match(r"^\s*", line).group(0) + "    "  # Add 4 spaces for method body
        
        # Check for indentation issues after super().__init__
        if in_init and "super().__init__" in line:
            # Fix indentation of the super line if needed
            if not line.startswith(init_indent):
                line = init_indent + line.lstrip()
                
            # If there's a next line, check its indentation
            if i + 1 < len(lines) and lines[i + 1].strip():
                next_line = lines[i + 1]
                if not next_line.startswith(init_indent):
                    lines[i + 1] = init_indent + next_line.lstrip()
        
        # Track when we exit __init__ method
        if in_init and line.strip() and re.search(r"^\s*def\s+", line):
            in_init = False
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fallback_upgrade(content: str, config_section: str) -> str:
    """
    Upgrade script content to use BaseScript using regex patterns.
    
    Args:
        content: Original script content
        config_section: Configuration section name
        
    Returns:
        Upgraded script content
    """
    # Add the import if not present
    if BASESCRIPT_IMPORT not in content:
        import_pattern = r"(import logging.*?)(\n\n)"
        if re.search(import_pattern, content):
            content = re.sub(
                import_pattern, 
                r"\1\nimport dewey.core.base_script\nfrom dewey.core.base_script import BaseScript\2", 
                content
            )
        else:
            # No existing logging import, add both
            content = re.sub(
                r"(import .*?)(\n\n)",
                r"\1\nimport logging\nfrom dewey.core.base_script import BaseScript\2",
                content
            )
            if "import " not in content:
                # No imports at all, add at the top
                content = f"import logging\nfrom dewey.core.base_script import BaseScript\n\n{content}"
    
    # Make the class inherit from BaseScript
    content = re.sub(
        r"class (\w+)(?:\([\w\.]+\))?:",
        r"class \1(BaseScript):",
        content
    )
    
    # Add super().__init__ call if it doesn't exist
    init_pattern = r"def __init__\(self(?:,\s*[^)]*?)?\):\s*\n((?:[ \t]+.*\n)*)"
    if re.search(init_pattern, content):
        def add_super_init(match):
            init_method = match.group(0)
            indentation = re.search(r'(\s+)', init_method).group(1)
            if 'super().__init__' not in init_method:
                # Find where to insert super().__init__
                after_def_line = init_method.split('\n')[0] + '\n'
                rest_of_method = init_method[len(after_def_line):]
                return f"{after_def_line}{indentation}super().__init__(config_section='{config_section}')\n{rest_of_method}"
            return init_method
        
        content = re.sub(init_pattern, add_super_init, content)
    else:
        # No __init__ method, add one with appropriate indentation
        # First, find the class definition and its indentation
        class_match = re.search(r"([ \t]*)class (\w+)\(BaseScript\):", content)
        if class_match:
            class_indent = class_match.group(1)
            class_name = class_match.group(2)
            method_indent = class_indent + "    "
            
            # Find where to insert the __init__ method
            class_def_line = class_match.group(0)
            class_start_pos = content.find(class_def_line) + len(class_def_line) + 1
            
            # Insert after class definition or after docstring if present
            next_line_match = re.search(r"\n([ \t]*\S)", content[class_start_pos:])
            if next_line_match:
                insert_pos = class_start_pos + next_line_match.start()
                init_method = f"\n{method_indent}def __init__(self):\n{method_indent}    super().__init__(config_section='{config_section}')\n"
                content = content[:insert_pos] + init_method + content[insert_pos:]
    
    # Replace logger references with self.logger
    content = re.sub(r"(?<!\.)logger\.", r"self.logger.", content)
    
    # Fix any indentation issues
    return fix_indentation(content)

def fix_indentation(content: str) -> str:
    """
    Fix common indentation issues in upgraded script content.
    
    Args:
        content: Script content to fix
        
    Returns:
        Fixed script content
    """
    # Fix indentation after super().__init__ call
    lines = content.splitlines()
    fixed_lines = []
    
    in_class = False
    class_indent = ""
    method_indent = ""
    
    for i, line in enumerate(lines):
        # Track class and method indentation levels
        if re.match(r'^\s*class\s+\w+', line):
            in_class = True
            class_indent = re.match(r'^(\s*)', line).group(1)
            method_indent = class_indent + "    "
            fixed_lines.append(line)
            continue
            
        # Fix super().__init__ indentation and the line after it
        if 'super().__init__' in line:
            # Ensure it has the correct indentation
            if not line.startswith(method_indent + "    "):
                line = method_indent + "    " + line.lstrip()
                
            fixed_lines.append(line)
            
            # Check if the next line needs indentation fixing
            if i + 1 < len(lines) and lines[i+1].strip() and not re.match(r'^\s', lines[i+1]):
                lines[i+1] = method_indent + "    " + lines[i+1].lstrip()
            continue
        
        # Fix other indentation issues
        if in_class and line.strip() and not line.startswith(class_indent):
            # This is a class member but indentation is wrong
            if re.match(r'^\s*def\s+', line):  # Method definition
                if not line.startswith(method_indent):
                    line = method_indent + line.lstrip()
            elif line.strip() and not re.match(r'^\s', line):  # Class attribute with no indentation
                line = method_indent + line
                
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def update_script_in_repo(script_name: str, content: str) -> bool:
    """
    Update a script in the repository.
    
    Args:
        script_name: Script filename
        content: New script content
        
    Returns:
        True if successful
    """
    # Find existing script in repo
    existing_path = get_existing_script_path(script_name)
    if not existing_path:
        logger.warning(f"Cannot find {script_name} in repository")
        return False
    
    # Backup original file
    backup_dir = REPO_ROOT / "backups" / "script_upgrader"
    backup_dir.mkdir(exist_ok=True, parents=True)
    backup_path = backup_dir / f"{script_name}.bak"
    
    try:
        with open(existing_path, 'r') as f:
            original_content = f.read()
        
        with open(backup_path, 'w') as f:
            f.write(original_content)
        
        logger.info(f"Backed up {existing_path} to {backup_path}")
        
        # Write new content
        with open(existing_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Updated {existing_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating {script_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Upgrade scripts to use BaseScript")
    parser.add_argument(
        "--xml-path", 
        type=Path, 
        default=REPOMIX_FILE,
        help="Path to repomix-output.xml (default: %(default)s)"
    )
    parser.add_argument(
        "--script", 
        type=str, 
        help="Process only this script (e.g., gmail_client.py)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Don't actually update files, just show what would happen"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Run a test with a small script to verify aider integration"
    )
    parser.add_argument(
        "--skip-aider", 
        action="store_true", 
        help="Skip using aider and use direct regex-based upgrading"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="",
        help="Specify the model for aider to use (e.g., --model gpt-4)"
    )
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Run a simple test if requested
    if args.test:
        return run_test(skip_aider=args.skip_aider, model=args.model)
    
    # Check if the XML file exists
    if not args.xml_path.exists():
        logger.error(f"XML file not found: {args.xml_path}")
        return 1
    
    # Parse the XML file
    script_contents = parse_repomix_xml(args.xml_path)
    if not script_contents:
        logger.error("No script content found in XML")
        return 1
    
    # Filter to specific script if requested
    if args.script:
        script_contents = {
            k: v for k, v in script_contents.items() 
            if k.endswith(args.script)
        }
        if not script_contents:
            logger.error(f"Script {args.script} not found in XML")
            return 1
    
    # Process each script
    success_count = 0
    failed_scripts = []
    success_method = {"aider": 0, "direct": 0}
    already_using_basescript = 0
    
    for path, content in script_contents.items():
        script_name = os.path.basename(path)
        logger.info(f"Processing {script_name}")
        
        # Find existing script
        existing_path = get_existing_script_path(script_name)
        
        # Check if script already uses BaseScript
        if is_script_using_basescript(content):
            logger.info(f"{script_name} already uses BaseScript")
            already_using_basescript += 1
            success_count += 1
            continue
        
        # Upgrade the script content
        try:
            upgrade_result = upgrade_script_content(
                content, 
                script_name, 
                existing_path,
                skip_aider=args.skip_aider,
                model=args.model,
                return_method=True
            )
            
            if isinstance(upgrade_result, tuple):
                upgraded_content, method = upgrade_result
                success_method[method] += 1
            else:
                upgraded_content = upgrade_result
                
            if args.dry_run:
                logger.info(f"Would update {script_name} (dry run)")
                success_count += 1
                # Optionally show diff
                continue
            
            # Update the script in the repo
            if update_script_in_repo(script_name, upgraded_content):
                success_count += 1
            else:
                failed_scripts.append(script_name)
        except Exception as e:
            logger.error(f"Error upgrading {script_name}: {e}")
            failed_scripts.append(script_name)
    
    # Print summary
    total_scripts = len(script_contents)
    logger.info("\n" + "=" * 40)
    logger.info(f"UPGRADE SUMMARY")
    logger.info(f"Total scripts processed: {total_scripts}")
    logger.info(f"Scripts already using BaseScript: {already_using_basescript}")
    logger.info(f"Successfully upgraded: {success_count} ({success_count/total_scripts*100:.1f}%)")
    if not args.skip_aider:
        logger.info(f"  - Using aider: {success_method['aider']}")
    logger.info(f"  - Using direct method: {success_method['direct']}")
    
    if failed_scripts:
        logger.info(f"Failed to upgrade: {len(failed_scripts)}")
        logger.info("Failed scripts:")
        for script in failed_scripts:
            logger.info(f"  - {script}")
    
    logger.info("=" * 40)
    
    return 0 if len(failed_scripts) == 0 else 1

def run_test(skip_aider: bool = False, model: str = ""):
    """
    Run a test with a small script to verify aider integration.
    
    Args:
        skip_aider: Skip using aider
        model: Model to use with aider
    """
    logger.info("Running test to verify integration")
    
    test_script = """
import logging

logger = logging.getLogger(__name__)

class TestScript:
    def __init__(self):
        self.name = "test"
        logger.info("Initialized test script")
        
    def run(self):
        logger.info("Running test script")
        return "Test successful"
"""
    
    # Upgrade the test script
    logger.info("Upgrading test script")
    upgraded_content = upgrade_script_content(test_script, "test_script.py", skip_aider=skip_aider, model=model)
    
    # Check if the script was properly upgraded
    success = is_script_using_basescript(upgraded_content)
    
    # Check for logger replacement
    success = success and "self.logger.info" in upgraded_content
    
    if success:
        logger.info("Test passed! Script was successfully upgraded.")
        logger.info("\nUpgraded content:\n" + "="*40 + "\n" + upgraded_content)
        return 0
    else:
        logger.error("Test failed! Script was not properly upgraded.")
        logger.error("\nResult:\n" + "="*40 + "\n" + upgraded_content)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 