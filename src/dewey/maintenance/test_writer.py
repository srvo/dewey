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
        """Initialize LLM model using aider's native configuration."""
        model_name = "Qwen/QwQ-32B"
        self.model = Model(f"deepinfra/{model_name}")

    def _validate_config(self):
        """Validate required configuration values."""
        # Check for required top-level sections
        if "core" not in self.config:
            raise ValueError("Missing required 'core' section in config")
            
        # Check for required keys within sections
        required_core_keys = ["project_root"]
        for key in required_core_keys:
            if key not in self.config["core"]:
                raise ValueError(f"Missing required core config key: {key}")
                
        if "llm" not in self.config:
            raise ValueError("Missing required 'llm' section in config")

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
        - Tests inherit from BaseScript when appropriate
        - All error handling uses try-except blocks with proper logging
        - Structured logging follows config/dewey.yaml settings
        - Type hints are strictly enforced for all function signatures
        - Configuration is loaded from central config (never hardcoded)
        - Tests cover normal cases, edge cases, and error handling
        - Use pytest fixtures where appropriate
        - Avoid mocking external dependencies - test against real implementations
        - Follow Arrange-Act-Assert pattern
        - Include type hints and descriptive docstrings
        - Validate both happy paths and error conditions
        - Match existing test patterns in our codebase
        - Include integration tests for critical paths
        - Use Ibis testing framework for database interactions
        - Follow DuckDB SQL Logic Test patterns where applicable
        - Adhere to all conventions in CONVENTIONS.md including:
          * PEP8 style guidelines
          * Google-style docstrings
          * 4-space indentation
          * 100 character line length
          * Explicit type hints
          * Error handling best practices
        
        Generate the test suite in a single file with:
        - All necessary imports
        - Proper setup/teardown
        - Type hints and docstrings
        - Clear test names following test_<function>_<scenario> pattern
        """

    def _get_test_path(self, source_path: Path) -> Path:
        """Mirror source directory structure under tests directory with '_test' suffix."""
        relative_path = source_path.relative_to(self.config["core"]["project_root"])
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
            
            response = coder.run(prompt)
            if not response:
                return None
                
            test_path = self._get_test_path(source_path)
            self._write_test_file(test_path, response)
            return response
            
        except Exception as e:
            logging.error(f"Error processing {source_path}: {str(e)}")
            return None

    def generate_tests_for_directory(self, source_dir: Path) -> Dict[Path, bool]:
        """Process all Python files in directory with individual commands.

        Args:
            source_dir (Path): Directory containing source files to process

        Returns:
            Dict[Path, bool]: Mapping of file paths to success status
        """
        results = {}
        files = []
        
        # First collect all files to process
        for root, _, filenames in os.walk(source_dir):
            for file in filenames:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    files.append(full_path)
                    results[full_path] = False

        # Process each file with its own command
        for file_path in files:
            try:
                # Create new Coder instance per file
                with open(file_path, "r") as f:
                    code = f.read()
                
                prompt = self._construct_test_prompt(code)
                coder = Coder.create(
                    main_model=self.model,
                    fnames=[str(file_path)],
                    io=self.io,
                    auto_commits=False,
                    dirty_commits=False
                )
                
                response = coder.run(prompt)
                if not response:
                    continue
                    
                test_path = self._get_test_path(file_path)
                self._write_test_file(test_path, response)
                results[file_path] = True
                
            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                results[file_path] = False

        return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate test suites using LLM-powered test writer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "source", 
        help="Root directory to recursively process (e.g. src/dewey) or specific file"
    )
    parser.add_argument(
        "--test-root", 
        default="tests",
        help="Root directory for test output (mirrors source structure)"
    )
    
    args = parser.parse_args()
    
    writer = TestWriter()
    if args.test_root:
        writer.test_root = Path(args.test_root)
        
    source_path = Path(args.source)
    if source_path.is_dir():
        writer.generate_tests_for_directory(source_path)
    else:
        writer.generate_tests_for_file(source_path)
