"""Automated test generation system leveraging LLMs to create comprehensive test suites.

Implements patterns from Assembled's testing approach with AI integration while adhering
to Dewey project conventions and testing philosophy.

Attributes:
    config (dict): Loaded project configuration
    io (InputOutput): I/O handler for user interaction
    max_workers (int): Maximum parallel workers for test generation
    test_root (Path): Root directory for test output
    llm_client (DeepInfraClient): Configured LLM API client
    model (Model): Initialized LLM model instance
"""

import os
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List

try:
    from aider.coders import Coder
    from aider.models import Model
    from aider.io import InputOutput
except ImportError as e:
    raise RuntimeError(
        "Missing required 'aider-chat' dependency. Install with:\n"
        "uv pip install 'aider-chat @ git+https://github.com/paul-gauthier/aider.git'\n"
        f"Original error: {str(e)}"
    )

from dewey.utils import load_config, get_llm_client, validate_test_output


class TestWriter:
    """Orchestrates automated test generation using LLMs while maintaining project conventions."""
    
    def __init__(self, max_workers: int = 4) -> None:
        """Initialize TestWriter with project configuration and LLM setup.

        Args:
            max_workers (int): Maximum parallel workers for test generation. Defaults to 4.
        """
        self.config = load_config()
        self.io = InputOutput(yes=True)
        self.max_workers = max_workers
        self.test_root = Path(self.config["core"]["project_root"]) / "tests"
        self.llm_client = get_llm_client()
        
        self._init_model()
        self._validate_config()

    def _init_model(self):
        """Initialize LLM model with project-specific configuration."""
        model_name = self.config["llm"]["providers"]["deepinfra"]["default_model"]
        self.model = Model(
            model_name,
            api_base="https://api.deepinfra.com/v1/openai",
            api_key=self.llm_client.client.api_key
        )

    def _validate_config(self):
        """Validate required configuration values."""
        required_keys = ["project_root", "llm"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

    def _construct_test_prompt(self, code: str) -> str:
        """Build structured prompt following Assembled's testing methodology.

        Args:
            code (str): Source code to generate tests for

        Returns:
            str: Structured prompt for LLM test generation
        """
        return f"""
        Help me write comprehensive tests for this code following Dewey project conventions:
        
        <function_to_test>
        {code}
        </function_to_test>
        
        Please ensure:
        - Tests cover normal cases, edge cases, and error handling
        - Use pytest fixtures where appropriate
        - Follow Arrange-Act-Assert pattern
        - Include type hints and descriptive docstrings
        - Validate both happy paths and error conditions
        - Match existing test patterns in our codebase
        - Include integration tests for critical paths
        - Use Ibis testing framework for database interactions
        - Follow DuckDB SQL Logic Test patterns where applicable
        
        Generate the test suite in a single file with:
        - All necessary imports
        - Proper setup/teardown
        - Type hints and docstrings
        - Clear test names following test_<function>_<scenario> pattern
        """

    def _get_test_path(self, source_path: Path) -> Path:
        """Mirror source directory structure under tests directory with '_test' suffix."""
        relative_path = source_path.relative_to(self.config["project_root"])
        test_dir = self.test_root / relative_path.parent
        test_file = test_dir / f"test_{relative_path.name}"
        return test_file

    def _write_test_file(self, test_path: Path, content: str):
        """Write generated tests to appropriate location with directory creation."""
        try:
            test_path.parent.mkdir(parents=True, exist_ok=True)
            with open(test_path, "w") as f:
                f.write(content)
            logging.info(f"Successfully wrote tests to {test_path}")
        except Exception as e:
            logging.error(f"Failed to write tests to {test_path}: {str(e)}")

    def generate_tests_for_file(self, source_path: Path) -> Optional[str]:
        """Generate test suite for a single file using LLM-powered test writer."""
        try:
            with open(source_path, "r") as f:
                code = f.read()
                
            prompt = self._construct_test_prompt(code)
            coder = Coder.create(
                main_model=self.model,
                fnames=[str(source_path)],
                io=self.io,
                auto_commits=False,
                dirty_commits=False
            )
            
            response = coder.run(prompt, temperature=0.2)
            if not response:
                return None
                
            test_path = self._get_test_path(source_path)
            self._write_test_file(test_path, response)
            return response
            
        except Exception as e:
            logging.error(f"Error processing {source_path}: {str(e)}")
            return None

    def generate_tests_for_directory(self, source_dir: Path) -> Dict[Path, bool]:
        """Process all Python files in directory with parallel execution.

        Args:
            source_dir (Path): Directory containing source files to process

        Returns:
            Dict[Path, bool]: Mapping of file paths to success status
        """
        results = {}
        futures = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith(".py"):
                        full_path = Path(root) / file
                        future = executor.submit(self.generate_tests_for_file, full_path)
                        futures.append(future)
                        results[full_path] = False
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results[future._args[0]] = True
                except Exception as e:
                    logging.error(f"Error processing {future._args[0]}: {str(e)}")
        
        return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test suites using LLM-powered test writer")
    parser.add_argument("source", help="Source directory or file to process")
    parser.add_argument("--test-root", help="Root directory for test output")
    
    args = parser.parse_args()
    
    writer = TestWriter()
    if args.test_root:
        writer.test_root = Path(args.test_root)
        
    source_path = Path(args.source)
    if source_path.is_dir():
        writer.generate_tests_for_directory(source_path)
    else:
        writer.generate_tests_for_file(source_path)
