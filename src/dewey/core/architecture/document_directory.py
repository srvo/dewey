
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from dewey.core.base_script import BaseScript
from dewey.llm.llm_utils import generate_content

# Load environment variables from .env file
load_dotenv()

CONVENTIONS_PATH = Path("../.aider/CONVENTIONS.md")


class DirectoryDocumenter(BaseScript):
    """Document directories with code analysis, quality checks, and structural validation."""

    def __init__(self, root_dir: str = ".") -> None:
        """Initializes the DirectoryDocumenter.

        Args:
            root_dir: The root directory to document. Defaults to the current directory.
        """
        super().__init__(config_section="architecture", name="DirectoryDocumenter")
        self.root_dir = Path(root_dir).resolve()
        self._validate_directory()

        self.conventions_path = CONVENTIONS_PATH  # Relative path to CONVENTIONS.md
        self.checkpoint_file = self.root_dir / ".dewey_documenter_checkpoint.json"
        self.checkpoints: Dict[str, str] = self._load_checkpoints()
        self.conventions: str = self._load_conventions()

        if not self.conventions_path.exists():
            self.logger.error(
                f"Could not find CONVENTIONS.md at {self.conventions_path}. Please ensure the path is correct.",
            )
            sys.exit(1)

    def _validate_directory(self) -> None:
        """Ensure directory exists and is accessible.

        Raises:
            FileNotFoundError: If the directory does not exist.
            PermissionError: If the directory is not accessible.
        """
        if not self.root_dir.exists():
            msg = f"Directory not found: {self.root_dir}"
            raise FileNotFoundError(msg)
        if not os.access(self.root_dir, os.R_OK):
            msg = f"Access denied to directory: {self.root_dir}"
            raise PermissionError(msg)

    def _load_conventions(self) -> str:
        """Load project coding conventions from CONVENTIONS.md.

        Returns:
            The content of the CONVENTIONS.md file.

        Raises:
            FileNotFoundError: If the CONVENTIONS.md file is not found.
            Exception: If there is an error loading the conventions.
        """
        try:
            with open(self.conventions_path) as f:
                return f.read()
        except FileNotFoundError:
            self.logger.exception(
                f"Could not find CONVENTIONS.md at {self.conventions_path}. Please ensure the path is correct.",
            )
            sys.exit(1)
        except Exception as e:
            self.logger.exception(f"Failed to load conventions: {e}")
            sys.exit(1)

    def _load_checkpoints(self) -> Dict[str, str]:
        """Load checkpoint data from file.

        Returns:
            A dictionary containing the checkpoint data.
        """
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(
                    f"Could not load checkpoint file: {e}. Starting from scratch.",
                )
                return {}
        return {}

    def _save_checkpoints(self) -> None:
        """Save checkpoint data to file."""
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump(self.checkpoints, f, indent=4)
        except Exception as e:
            self.logger.exception(f"Could not save checkpoint file: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file contents with size check.

        Args:
            file_path: The path to the file.

        Returns:
            The SHA256 hash of the file contents.

        Raises:
            Exception: If the hash calculation fails.
        """
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return "empty_file"
            with open(file_path, "rb") as f:
                return f"{file_size}_{hashlib.sha256(f.read()).hexdigest()}"
        except Exception as e:
            self.logger.exception(f"Hash calculation failed for {file_path}: {e}")
            raise

    def _is_checkpointed(self, file_path: Path) -> bool:
        """Check if a file has been processed based on content hash.

        Args:
            file_path: The path to the file.

        Returns:
            True if the file has been processed, False otherwise.
        """
        try:
            current_hash = self._calculate_file_hash(file_path)
            return self.checkpoints.get(str(file_path)) == current_hash
        except Exception as e:
            self.logger.exception(f"Could not read file to check checkpoint: {e}")
            return False

    def _checkpoint(self, file_path: Path) -> None:
        """Checkpoint a file by saving its content hash.

        Args:
            file_path: The path to the file.
        """
        try:
            with open(file_path) as f:
                content = f.read()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            self.checkpoints[str(file_path)] = content_hash
            self._save_checkpoints()
        except Exception as e:
            self.logger.exception(f"Could not checkpoint file: {e}")

    def analyze_code(self, code: str) -> Tuple[str, Optional[str]]:
        """Analyzes the given code using an LLM and returns a summary.

        Args:
            code: The code to analyze.

        Returns:
            A tuple containing the analysis and the suggested module.
        """
        prompt = f"""
        Analyze the following code and provide:
        1.  A summary of its functionality, its dependencies, any potential issues or improvements based on the following conventions.
        2.  Whether the code contains placeholder code (e.g., "pass", "TODO", "NotImplementedError").
        3.  Whether it appears to be related to the Dewey project (e.g., by using project-specific imports or code patterns).
        4.  Suggest a target module within the Dewey project structure (e.g., "core.crm", "llm.api_clients", "utils") for this code.
            If the code doesn't fit neatly into an existing module, suggest a new module name.
            Just return the module name, or None if it's unclear.

        {self.conventions}

        ```python
        {code}
        ```
        """
        try:
            response = generate_content(self.llm_client, prompt)
            # Split the response into analysis and suggested module
            parts = response.split("4.")
            analysis = parts[0].strip()
            suggested_module = (
                parts[1]
                .strip()
                .replace(
                    "Suggest a target module within the Dewey project structure", "", )
                .replace(":", "")
                .strip()
                if len(parts) > 1
                else None
            )
            return analysis, suggested_module
        except Exception as e:
            self.logger.exception(f"Unexpected error during code analysis: {e}")
            raise

    def _analyze_code_quality(self, file_path: Path) -> Dict[str, List[str]]:
        """Run code quality checks using flake8 and ruff.

        Args:
            file_path: The path to the file.

        Returns:
            A dictionary containing the results of the code quality checks.
        """
        results: Dict[str, List[str]]=None, "ruff": []}
        try:
            # Run flake8
            flake8_result=None, str(file_path)], capture_output=True, text=True, check=False, )
            results["flake8"] = flake8_result.stdout.splitlines()

            # Run ruff
            ruff_result = subprocess.run(
                ["ruff", "check", str(file_path)], capture_output=True, text=True, check=False, )
            results["ruff"] = ruff_result.stdout.splitlines()
        except Exception as e:
            self.logger.exception(f"Code quality analysis failed: {e}")
        return results

    def _analyze_directory_structure(self) -> Dict[str, Any]:
        """Check directory structure against project conventions.

        Returns:
            A dictionary containing the directory structure analysis.
        """
        expected_modules = [
            "src/dewey/core", "src/dewey/llm", "src/dewey/pipeline", "src/dewey/utils", "ui/screens", "ui/components", "config", "tests", "docs", ]

        dir_structure: Dict[str, Any]=None, dirs, files in os.walk(self.root_dir):
            if List[str]] is None:
                List[str]] = {"flake8": []
            if "ruff": []}
        try:
            # Run flake8
            flake8_result is None:
                "ruff": []}
        try:
            # Run flake8
            flake8_result = subprocess.run(
                ["flake8"
            if Any] is None:
                Any] = {}
        deviations: List[str] = []

        for root
            rel_path = Path(root).relative_to(self.root_dir)
            if any(part.startswith(".") for part in rel_path.parts):
                continue

            dir_structure[str(rel_path)] = {
                "files": files,
                "subdirs": dirs,
                "expected": any(str(rel_path).startswith(m) for m in expected_modules),
            }

            if not dir_structure[str(rel_path)]["expected"] and rel_path != Path():
                deviations.append(str(rel_path))

        return {"structure": dir_structure, "deviations": deviations}

    def generate_readme(self, directory: Path, analysis_results: Dict[str, str]) -> str:
        """Generate comprehensive README with quality and structure analysis.

        Args:
            directory: The directory to generate the README for.
            analysis_results: A dictionary containing the analysis results.

        Returns:
            The content of the README file.
        """
        dir_analysis = self._analyze_directory_structure()

        readme_content = [
            f"# {directory.name} Documentation",
            "\n## Code Analysis",
            *[f"### {fn}\n{analysis}" for fn, analysis in analysis_results.items()],
            "\n## Code Quality",
            *[
                f"### {fn}\n- Flake8: {len(data['flake8'])} issues\n- Ruff: {len(data['ruff'])} issues"
                for fn, data in analysis_results.items()
                if "code_quality" in data
            ],
            "\n## Directory Structure",
            f"- Expected Modules: {', '.join(dir_analysis['expected_modules'])}",
            f"- Structural Deviations ({len(dir_analysis['deviations'])}):",
            *[f"  - {d}" for d in dir_analysis["deviations"]],
            "\n## Future Development Plans\nTBD",
        ]

        return "\n".join(readme_content)

    def correct_code_style(self, code: str) -> str:
        """Corrects the code style of the given code using an LLM based on project conventions.

        Args:
            code: The code to correct.

        Returns:
            The corrected code.
        """
        prompt = f"""
        Correct the style of the following code to adhere to these conventions:

        {self.conventions}

        ```python
        {code}
        ```
        Return only the corrected code.
        """
        try:
            return generate_content(self.llm_client, prompt)
        except Exception as e:
            self.logger.exception(f"LLM failed to correct code style: {e}")
            raise

    def suggest_filename(self, code: str) -> Optional[str]:
        """Suggests a more human-readable filename for the given code using an LLM.

        Args:
            code: The code to suggest a filename for.

        Returns:
            The suggested filename.
        """
        prompt = f"""
        Suggest a concise, human-readable filename (without the .py extension) for a Python script
        that contains the following code.  The filename should be lowercase and use underscores
        instead of spaces.

        ```python
        {code}
        ```
        """
        try:
            return generate_content(self.llm_client, prompt).strip()
        except Exception as e:
            self.logger.exception(f"LLM failed to suggest filename: {e}")
            return None

    def process_directory(self, directory: str) -> None:
        """Processes the given directory, analyzes its contents, and generates a README.md file.

        Args:
            directory: The directory to process.
        """
        directory_path = Path(directory).resolve()

        if not directory_path.exists() or not directory_path.is_dir():
            self.logger.error(f"Directory '{directory}' not found.")
            return

        analysis_results: Dict[str, str] = {}
        for filename in os.listdir(directory_path):
            file_path = directory_path / filename
            if file_path.suffix == ".py":
                if self._is_checkpointed(file_path):
                    self.logger.info(f"Skipping checkpointed file: {filename}")
                    continue

                try:
                    with open(file_path) as f:
                        code = f.read()

                    # Basic check for project-related code
                    if "src.dewey" not in code and "from dewey" not in code:
                        self.logger.warning(
                            f"Skipping {filename}: Not related to Dewey project.",
                        )
                        continue

                    analysis, suggested_module = self.analyze_code(code)
                    analysis_results[filename] = analysis

                    # Determine the target path
                    if suggested_module:
                        target_dir = (
                            self.root_dir
                            / "src"
                            / "dewey"
                            / suggested_module.replace(".", "/")
                        )
                        target_dir.mkdir(
                            parents=True,
                            exist_ok=True,
                        )  # Ensure the directory exists
                        target_path = target_dir / filename
                        move_file = input(
                            f"Move {filename} to {target_path}? (y/n): ",
                        ).lower()
                        if move_file == "y":
                            try:
import shutil

                                shutil.move(file_path, target_path)
                                self.logger.info(f"Moved {filename} to {target_path}")
                                file_path = target_path
                            except Exception as e:
                                self.logger.exception(
                                    f"Failed to move {filename} to {target_path}: {e}",
                                )
                        else:
                            self.logger.info(f"Skipped moving {filename}.")

                    # Suggest a better filename
                    suggested_filename = self.suggest_filename(code)
                    if suggested_filename:
                        new_file_path = file_path.parent / (suggested_filename + ".py")
                        rename_file = input(
                            f"Rename {filename} to {suggested_filename + '.py'}? (y/n): ",
                        ).lower()
                        if rename_file == "y":
                            try:
                                os.rename(file_path, new_file_path)
                                self.logger.info(
                                    f"Renamed {filename} to {suggested_filename + '.py'}",
                                )
                                file_path = (
                                    new_file_path  # Update file_path to the new name
                                )
                            except Exception as e:
                                self.logger.exception(
                                    f"Failed to rename {filename} to {suggested_filename + '.py'}: {e}",
                                )
                        else:
                            self.logger.info(f"Skipped renaming {filename}.")

                    # Ask for confirmation before correcting code style
                    correct_style = input(
                        f"Correct code style for {filename}? (y/n): ",
                    ).lower()
                    if correct_style == "y":
                        corrected_code = self.correct_code_style(code)
                        if corrected_code:
                            # Ask for confirmation before writing the corrected code to file
                            write_corrected = input(
                                f"Write corrected code to {filename}? (y/n): ",
                            ).lower()
                            if write_corrected == "y":
                                try:
                                    with open(file_path, "w") as f:
                                        f.write(corrected_code)
                                    self.logger.info(
                                        f"Corrected code style for {filename} and wrote to file.",
                                    )
                                except Exception as e:
                                    self.logger.exception(
                                        f"Failed to write corrected code to {filename}: {e}",
                                    )
                            else:
                                self.logger.info(
                                    f"Corrected code style for {filename}, but did not write to file.",
                                )
                        else:
                            self.logger.warning(
                                f"Failed to correct code style for {filename}.",
                            )
                    else:
                        self.logger.info(f"Skipped correcting code style for {filename}.")

                    self._checkpoint(file_path)  # Checkpoint after processing

                except Exception as e:
                    self.logger.exception(f"Failed to process {filename}: {e}")

        readme_content = self.generate_readme(directory_path, analysis_results)
        readme_path = directory_path / "README.md"
        try:
            with open(readme_path, "w") as f:
                f.write(readme_content)
            self.logger.info(f"Generated README.md for {directory}")
        except Exception as e:
            self.logger.exception(f"Failed to write README.md: {e}")

    def run(self) -> None:
        """Processes the entire project directory."""
        for root, _, _files in os.walk(self.root_dir):
            self.process_directory(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Document a directory by analyzing its contents and generating a README file.",
    )
    parser.add_argument(
        "--directory",
        help="The directory to document (defaults to project root).",
        default=".",
    )
    args = parser.parse_args()

    documenter = DirectoryDocumenter(root_dir=args.directory)
    documenter.execute()
