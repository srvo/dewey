import os
import sys
import logging
import argparse
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Assuming these are in the same relative location as the script
try:
    from src.llm.api_clients.gemini import GeminiClient
    from src.llm.api_clients.deepinfra import DeepInfraClient
    from src.llm.exceptions import LLMError
except ImportError as e:
    print(f"Error: Could not import necessary modules: {e}. Make sure you are running this script from the project root and dependencies are installed.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectoryDocumenter:
    """
    A tool to document directories by analyzing their contents and generating README files.
    """

    def __init__(self, root_dir: str = "."):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        deepinfra_api_key = os.getenv("DEEPINFRA_API_KEY")

        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not found in .env. Gemini client may not function correctly.")
        if not deepinfra_api_key:
            logger.warning("DEEPINFRA_API_KEY not found in .env. DeepInfra client may not function correctly.")

        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        self.deepinfra_client = DeepInfraClient(api_key=deepinfra_api_key)
        self.conventions_path = Path("../.aider/CONVENTIONS.md")  # Relative path to CONVENTIONS.md
        self.root_dir = Path(root_dir).resolve()
        self.checkpoint_file = self.root_dir / ".dewey_documenter_checkpoint.json"
        self.checkpoints = self._load_checkpoints()

        if not self.conventions_path.exists():
            logger.error(f"Could not find CONVENTIONS.md at {self.conventions_path}. Please ensure the path is correct.")
            sys.exit(1)

        self.conventions = self._load_conventions()

    def _load_conventions(self) -> str:
        """Load the project's coding conventions from CONVENTIONS.md."""
        try:
            with open(self.conventions_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Could not find CONVENTIONS.md at {self.conventions_path}. Please ensure the path is correct.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load conventions: {e}")
            sys.exit(1)

    def _load_checkpoints(self) -> Dict[str, str]:
        """Load checkpoint data from file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load checkpoint file: {e}. Starting from scratch.")
                return {}
        return {}

    def _save_checkpoints(self) -> None:
        """Save checkpoint data to file."""
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump(self.checkpoints, f, indent=4)
        except Exception as e:
            logger.error(f"Could not save checkpoint file: {e}")

    def _is_checkpointed(self, file_path: Path) -> bool:
        """Check if a file has been checkpointed based on its content hash."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            return self.checkpoints.get(str(file_path), None) == content_hash
        except Exception as e:
            logger.error(f"Could not read file to check checkpoint: {e}")
            return False

    def _checkpoint(self, file_path: Path) -> None:
        """Checkpoint a file by saving its content hash."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            self.checkpoints[str(file_path)] = content_hash
            self._save_checkpoints()
        except Exception as e:
            logger.error(f"Could not checkpoint file: {e}")

    def _get_llm_client(self):
        """
        Returns the Gemini client if available, otherwise falls back to the DeepInfra client.
        """
        return self.gemini_client, self.deepinfra_client

    def analyze_code(self, code: str) -> str:
        """
        Analyzes the given code using an LLM and returns a summary.
        """
        gemini_client, deepinfra_client = self._get_llm_client()
        prompt = f"""
        Analyze the following code and provide a summary of its functionality,
        its dependencies, and any potential issues or improvements based on the following conventions:

        {self.conventions}

        ```python
        {code}
        ```
        """
        try:
            return gemini_client.generate_content(prompt)
        except LLMError as e:
            logger.warning(f"Gemini rate limit exceeded, attempting DeepInfra fallback. GeminiError: {e}")
            try:
                return deepinfra_client.chat_completion(prompt=prompt)
            except Exception as e:
                logger.error(f"DeepInfra also failed: {e}")
                raise

    def generate_readme(self, directory: Path, analysis_results: Dict[str, str]) -> str:
        """
        Generates a README.md file for the given directory based on the analysis results.
        """
        readme_content = f"# {directory.name}\n\n"
        readme_content += "## Overview\n\n"
        for filename, analysis in analysis_results.items():
            readme_content += f"### {filename}\n{analysis}\n\n"

        readme_content += "## Plans\n\n Future development plans for this directory.\n"  # Add a section for future plans

        return readme_content

    def correct_code_style(self, code: str) -> str:
        """
        Corrects the code style of the given code using an LLM based on project conventions.
        """
        gemini_client, deepinfra_client = self._get_llm_client()
        prompt = f"""
        Correct the style of the following code to adhere to these conventions:

        {self.conventions}

        ```python
        {code}
        ```
        Return only the corrected code.
        """
        try:
            return gemini_client.generate_content(prompt)
        except LLMError as e:
            logger.warning(f"Gemini rate limit exceeded, attempting DeepInfra fallback. GeminiError: {e}")
            try:
                return deepinfra_client.chat_completion(prompt=prompt)
            except Exception as e:
                logger.error(f"DeepInfra also failed: {e}")
                raise

    def suggest_filename(self, code: str) -> str:
        """
        Suggests a more human-readable filename for the given code using an LLM.
        """
        gemini_client, deepinfra_client = self._get_llm_client()
        prompt = f"""
        Suggest a concise, human-readable filename (without the .py extension) for a Python script
        that contains the following code.  The filename should be lowercase and use underscores
        instead of spaces.

        ```python
        {code}
        ```
        """
        try:
            return gemini_client.generate_content(prompt).strip()
        except LLMError as e:
            logger.warning(f"Gemini rate limit exceeded, attempting DeepInfra fallback. GeminiError: {e}")
            try:
                return deepinfra_client.chat_completion(prompt=prompt).strip()
            except Exception as e:
                logger.error(f"DeepInfra also failed: {e}")
                return None

    def process_directory(self, directory: str) -> None:
        """
        Processes the given directory, analyzes its contents, and generates a README.md file.
        """
        directory_path = Path(directory).resolve()

        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory '{directory}' not found.")
            return

        analysis_results = {}
        for filename in os.listdir(directory_path):
            file_path = directory_path / filename
            if file_path.suffix == ".py":
                if self._is_checkpointed(file_path):
                    logger.info(f"Skipping checkpointed file: {filename}")
                    continue

                try:
                    with open(file_path, "r") as f:
                        code = f.read()
                        analysis = self.analyze_code(code)
                        analysis_results[filename] = analysis

                        # Suggest a better filename
                        suggested_filename = self.suggest_filename(code)
                        if suggested_filename:
                            new_file_path = directory_path / (suggested_filename + ".py")
                            rename_file = input(f"Rename {filename} to {suggested_filename + '.py'}? (y/n): ").lower()
                            if rename_file == 'y':
                                try:
                                    os.rename(file_path, new_file_path)
                                    logger.info(f"Renamed {filename} to {suggested_filename + '.py'}")
                                    file_path = new_file_path  # Update file_path to the new name
                                except Exception as e:
                                    logger.error(f"Failed to rename {filename} to {suggested_filename + '.py'}: {e}")
                            else:
                                logger.info(f"Skipped renaming {filename}.")

                        # Ask for confirmation before correcting code style
                        correct_style = input(f"Correct code style for {filename}? (y/n): ").lower()
                        if correct_style == 'y':
                            corrected_code = self.correct_code_style(code)
                            if corrected_code:
                                # Ask for confirmation before writing the corrected code to file
                                write_corrected = input(f"Write corrected code to {filename}? (y/n): ").lower()
                                if write_corrected == 'y':
                                    try:
                                        with open(file_path, "w") as f:
                                            f.write(corrected_code)
                                        logger.info(f"Corrected code style for {filename} and wrote to file.")
                                    except Exception as e:
                                        logger.error(f"Failed to write corrected code to {filename}: {e}")
                                else:
                                    logger.info(f"Corrected code style for {filename}, but did not write to file.")
                            else:
                                logger.warning(f"Failed to correct code style for {filename}.")
                        else:
                            logger.info(f"Skipped correcting code style for {filename}.")

                    self._checkpoint(file_path)  # Checkpoint after processing

                except Exception as e:
                    logger.error(f"Failed to process {filename}: {e}")

        readme_content = self.generate_readme(directory_path, analysis_results)
        readme_path = directory_path / "README.md"
        try:
            with open(readme_path, "w") as f:
                f.write(readme_content)
            logger.info(f"Generated README.md for {directory}")
        except Exception as e:
            logger.error(f"Failed to write README.md: {e}")

    def process_project(self):
        """Processes the entire project directory."""
        for root, _, files in os.walk(self.root_dir):
            self.process_directory(root)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Document a directory by analyzing its contents and generating a README file.")
    parser.add_argument("--directory", help="The directory to document (defaults to project root).", default=".")
    args = parser.parse_args()

    documenter = DirectoryDocumenter(root_dir=args.directory)
    documenter.process_project()
