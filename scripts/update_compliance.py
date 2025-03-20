"""
Script to automatically update non-compliant files using Aider.

This script reads the list of non-compliant files and uses Aider to fix:
1. Inheritance from BaseScript
2. Config-based logging from dewey.yaml
3. Using paths from config.paths
4. Using settings from config.settings
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict

DEWEY_ROOT = Path("/Users/srvo/dewey")
CONFIG_PATH = DEWEY_ROOT / "config" / "dewey.yaml"
NON_COMPLIANT_DIR = DEWEY_ROOT / "scripts" / "non_compliant"

# Base message template for Aider
BASE_MESSAGE = '''
Please update this script to meet dewey's code standards:

1. Inherit from BaseScript (import from dewey.core.base_script)
   - Add necessary imports
   - Make the script a class that inherits from BaseScript
   - Move main functionality into a run() method
   - Add proper type hints and docstrings

2. Use config-based logging from /Users/srvo/dewey/config/dewey.yaml
   - Remove any direct logging configuration (basicConfig, handlers)
   - Use self.logger from BaseScript
   - Log at appropriate levels (debug, info, warning, error)

3. Use paths from config.paths
   - Replace hardcoded paths with self.config.paths
   - Common paths are in dewey.yaml under paths section
   - Use Path objects for path manipulation

4. Use settings from config.settings
   - Replace hardcoded settings with self.config.settings
   - API keys should use environment variables
   - Common settings are in dewey.yaml under settings section

Example structure:
```python
from pathlib import Path
from dewey.core.base_script import BaseScript

class MyScript(BaseScript):
    """Description of what this script does."""

    def run(self) -> None:
        """Main execution method."""
        self.logger.info("Starting script")
        data_dir = Path(self.config.paths.data_dir)
        api_key = self.config.settings.some_api_key
        # ... rest of the code ...
```
'''

def verify_environment() -> None:
    """Verify that all required paths and tools exist."""
    if not DEWEY_ROOT.exists():
        raise FileNotFoundError(f"Dewey root directory not found at {DEWEY_ROOT}")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    if not NON_COMPLIANT_DIR.exists():
        raise FileNotFoundError(f"Non-compliant files directory not found at {NON_COMPLIANT_DIR}")
    
    # Check if aider is installed
    try:
        subprocess.run(["aider", "--version"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        raise RuntimeError("Aider is not installed. Please install it with 'pip install aider-chat'")

def read_non_compliant_files() -> Dict[str, List[str]]:
    """Read the list of non-compliant files and their violations."""
    files = {}
    all_files_path = NON_COMPLIANT_DIR / "all_files.txt"
    
    if not all_files_path.exists():
        raise FileNotFoundError(f"all_files.txt not found at {all_files_path}")
    
    with open(all_files_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse file and violations
                parts = line.split('  # violations: ')
                if len(parts) == 2:
                    file_path, violations = parts
                    files[file_path] = violations.split(', ')
    
    return files

def create_aider_message(file_path: str, violations: List[str]) -> str:
    """Create a specific message for Aider based on the file's violations."""
    message = BASE_MESSAGE
    
    # Add specific guidance based on violations
    if 'base_script' in violations:
        message += "\nThis file needs to be converted to inherit from BaseScript."
    if 'config_logging' in violations:
        message += "\nRemove direct logging configuration and use self.logger from BaseScript."
    if 'config_paths' in violations:
        message += "\nReplace hardcoded paths with self.config.paths from dewey.yaml."
    if 'config_settings' in violations:
        message += "\nReplace hardcoded settings with self.config.settings from dewey.yaml."
    
    return message

def run_aider(file_path: str, message: str) -> bool:
    """Run Aider on a file with the given message."""
    try:
        # Change to the dewey root directory
        original_cwd = Path.cwd()
        os.chdir(DEWEY_ROOT)
        
        # Run Aider with the file and message
        cmd = [
            "aider",
            "--no-git",  # Don't create commits
            "--no-auto-commits",  # Don't auto-commit changes
            "--yes",  # Auto-accept changes
            file_path
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send the message to Aider
        stdout, stderr = process.communicate(input=message)
        
        # Change back to original directory
        os.chdir(original_cwd)
        
        if process.returncode != 0:
            print(f"Warning: Aider returned non-zero exit code for {file_path}")
            print(f"stderr: {stderr}")
            return False
            
        return True
    except Exception as e:
        print(f"Error running Aider on {file_path}: {e}")
        return False

def main():
    try:
        print("Verifying environment...")
        verify_environment()
        
        print("Reading non-compliant files...")
        files = read_non_compliant_files()
        
        print(f"\nFound {len(files)} files to update")
        
        # Process each file
        for file_path, violations in files.items():
            print(f"\nProcessing {file_path}")
            print(f"Violations: {', '.join(violations)}")
            
            message = create_aider_message(file_path, violations)
            success = run_aider(file_path, message)
            
            if success:
                print(f"✓ Successfully updated {file_path}")
            else:
                print(f"✗ Failed to update {file_path}")
        
        print("\nCompleted processing all files")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 