"""Script to extract non-compliant files from pytest output.

This script runs the compliance tests and extracts:
1. Files that don't inherit from BaseScript
2. Files that configure logging directly
3. Files that use hardcoded paths
4. Files that use hardcoded settings
"""

import ast
import os
import re
import subprocess
import sys

import yaml

DEWEY_ROOT = "/Users/srvo/dewey"
OUTPUT_DIR = os.path.join(DEWEY_ROOT, "scripts/non_compliant")


def verify_paths() -> None:
    """Verify that required paths exist."""
    if not os.path.exists(DEWEY_ROOT):
        raise ValueError(f"Dewey root directory not found at {DEWEY_ROOT}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_tests() -> str:
    """Run compliance tests and return output."""
    result = subprocess.run(
        ["pytest", "tests/dewey/core/test_script_compliance.py", "-v"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


def extract_files(test_output: str) -> dict[str, list[str]]:
    """Extract non-compliant files from test output."""
    non_compliant = {
        "base_script": [],
        "config_logging": [],
        "config_paths": [],
        "config_settings": [],
    }

    # Define patterns to match failure sections
    patterns = {
        "base_script": r"Failed: The following scripts do not inherit from BaseScript:\n((?:.*?/Users/srvo/dewey/.*?\n)+)",
        "config_logging": r"Failed: The following scripts configure logging directly instead of using dewey\.yaml:\n((?:.*?/Users/srvo/dewey/.*?\n)+)",
        "config_paths": r"Failed: The following scripts use hardcoded paths instead of config:\n((?:.*?/Users/srvo/dewey/.*?\n)+)",
        "config_settings": r"Failed: The following scripts use hardcoded settings instead of config:\n((?:.*?/Users/srvo/dewey/.*?\n)+)",
    }

    # Extract files for each category
    for category, pattern in patterns.items():
        matches = re.finditer(pattern, test_output, re.MULTILINE | re.DOTALL)
        for match in matches:
            file_list = match.group(1).strip().split("\n")
            # Clean up file paths and filter out empty lines and lines starting with E
            cleaned_paths = [
                path.strip().replace("E           ", "")
                for path in file_list
                if path.strip() and "/Users/srvo/dewey/" in path
            ]
            non_compliant[category].extend(cleaned_paths)

    return non_compliant


def analyze_file_for_configs(file_path: str) -> tuple[set[str], set[str]]:
    """Analyze a file for hardcoded paths and settings."""
    paths = set()
    settings = set()

    try:
        with open(file_path) as f:
            content = f.read()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    path = node.value
                    if any(path.startswith(prefix) for prefix in ["/", "~/", "./"]):
                        if not any(
                            path.startswith(ignore)
                            for ignore in ["/opt", "/usr", "/bin", "/etc"]
                        ):
                            paths.add(path)

                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id.upper()
                            if (
                                name.endswith("_URL")
                                or name.endswith("_KEY")
                                or name.endswith("_TOKEN")
                            ):
                                if isinstance(node.value, ast.Constant):
                                    settings.add(f"{name}: {node.value.value}")
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")

    return paths, settings


def analyze_needed_configs(non_compliant: dict[str, list[str]]) -> dict[str, set[str]]:
    """Analyze non-compliant files to determine needed config additions."""
    needed_configs = {"paths": set(), "settings": set()}

    # Analyze files that use hardcoded paths
    for file_path in non_compliant["config_paths"]:
        paths, _ = analyze_file_for_configs(file_path)
        needed_configs["paths"].update(paths)

    # Analyze files that use hardcoded settings
    for file_path in non_compliant["config_settings"]:
        _, settings = analyze_file_for_configs(file_path)
        needed_configs["settings"].update(settings)

    return needed_configs


def write_results(
    non_compliant: dict[str, list[str]], needed_configs: dict[str, set[str]]
) -> None:
    """Write results to output files."""
    # Write non-compliant files by category
    for category, files in non_compliant.items():
        if files:  # Only write files if the list is not empty
            output_file = os.path.join(OUTPUT_DIR, f"{category}.txt")
            with open(output_file, "w") as f:
                for file_path in sorted(files):
                    f.write(f"{file_path}\n")

    # Write config suggestions
    suggestions_file = os.path.join(OUTPUT_DIR, "config_suggestions.yaml")
    with open(suggestions_file, "w") as f:
        f.write("# Suggested additions to dewey.yaml\n\n")

        if needed_configs["paths"]:
            f.write("paths:\n")
            for path in sorted(needed_configs["paths"]):
                f.write(f"  {path.split('/')[-1].replace('.', '_').lower()}: {path}\n")

        if needed_configs["settings"]:
            f.write("\nsettings:\n")
            for setting in sorted(needed_configs["settings"]):
                name, value = setting.split(": ", 1)
                f.write(f"  {name.lower()}: {value}\n")

    # Write metadata
    metadata = {
        "summary": {category: len(files) for category, files in non_compliant.items()},
        "total_unique_files": len(
            set().union(*[set(files) for files in non_compliant.values()])
        ),
    }

    with open(os.path.join(OUTPUT_DIR, "metadata.yaml"), "w") as f:
        yaml.dump(metadata, f, default_flow_style=False)

    # Print summary
    print("\nSummary:")
    for category, count in metadata["summary"].items():
        print(f"{category}: {count} files")
    print(f"\nTotal unique files: {metadata['total_unique_files']}")
    print(f"Results written to {OUTPUT_DIR}/")
    print(
        "\nCheck scripts/non_compliant/config_suggestions.yaml for suggested dewey.yaml additions\n"
    )


def main():
    """Function main."""
    try:
        print("Verifying environment...")
        verify_paths()

        print("Running compliance tests...")
        test_output = run_tests()

        print("Extracting non-compliant files...")
        non_compliant = extract_files(test_output)

        print("\nAnalyzing files for needed configurations...")
        needed_configs = analyze_needed_configs(non_compliant)

        print("\nWriting results...")
        write_results(non_compliant, needed_configs)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
