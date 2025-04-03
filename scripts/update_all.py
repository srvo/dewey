"""Main script to orchestrate the compliance update process.

This script:
1. Runs compliance tests to identify non-compliant files
2. Extracts the list of non-compliant files
3. Uses Aider to update each file
4. Verifies the changes by running compliance tests again
"""

import subprocess
import sys
import time
from pathlib import Path

DEWEY_ROOT = Path("/Users/srvo/dewey")
CONFIG_PATH = DEWEY_ROOT / "config" / "dewey.yaml"
SCRIPTS_DIR = DEWEY_ROOT / "scripts"
OUTPUT_DIR = SCRIPTS_DIR / "non_compliant"


def verify_environment() -> None:
    """Verify that all required paths and tools exist."""
    if not DEWEY_ROOT.exists():
        raise FileNotFoundError(f"Dewey root directory not found at {DEWEY_ROOT}")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")

    # Ensure scripts directory exists
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check if aider is installed
    try:
        subprocess.run(["aider", "--version"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        raise RuntimeError(
            "Aider is not installed. Please install it with 'pip install aider-chat'"
        )


def run_script(script_name: str, description: str) -> bool:
    """Run a Python script and return True if successful."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        print(f"✗ Script not found: {script_path}")
        return False

    print(
        "\n================================================================================"
    )
    print(f"Running {script_name}...")
    print(f"Purpose: {description}")
    print(
        "================================================================================"
    )

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            text=True,
            capture_output=True,
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Script failed with exit code {e.returncode}")
        print(e.stdout)
        print(e.stderr)
        return False


def run_final_tests() -> bool:
    """Run compliance tests and return True if all pass."""
    print("\nRunning final compliance check...")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/dewey/core/test_script_compliance.py",
                "-v",
            ],
            check=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        print("✗ Some compliance tests still failing")
        print(
            "Review the output above and the generated files in scripts/non_compliant/"
        )
        return False


def main():
    """Function main."""
    try:
        start_time = time.time()
        print(f"Starting compliance update process at {time.asctime()}")
        print(f"Dewey root: {DEWEY_ROOT}")
        print(f"Config file: {CONFIG_PATH}\n")

        print("Verifying environment...")
        verify_environment()

        # Run extract_non_compliant.py to identify files
        if not run_script(
            "extract_non_compliant.py",
            "Identify files that don't meet dewey's code standards",
        ):
            sys.exit(1)

        # Run update_compliance.py to fix files
        if not run_script(
            "update_compliance.py", "Update non-compliant files to meet code standards"
        ):
            sys.exit(1)

        # Run final compliance check
        if not run_final_tests():
            sys.exit(1)

        end_time = time.time()
        duration = end_time - start_time
        print(f"\nCompliance update process completed in {duration:.2f} seconds")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
