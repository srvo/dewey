import os
import sys
import logging
import argparse
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

    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        deepinfra_api_key = os.getenv("DEEPINFRA_API_KEY")

        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not found in .env. Gemini client may not function correctly.")
        if not deepinfra_api_key:
            logger.warning("DEEPINFRA_API_KEY not found in .env. DeepInfra client may not function correctly.")

        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        self.deepinfra_client = DeepInfraClient(api_key=deepinfra_api_key)
        self.conventions_path = Path("../.aider/CONVENTIONS.md")  # Relative path to CONVENTIONS.md

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
                try:
                    with open(file_path, "r") as f:
                        code = f.read()
                        analysis = self.analyze_code(code)
                        analysis_results[filename] = analysis

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Document a directory by analyzing its contents and generating a README file.")
    parser.add_argument("directory", help="The directory to document.")
    args = parser.parse_args()

    documenter = DirectoryDocumenter()
    documenter.process_directory(args.directory)
