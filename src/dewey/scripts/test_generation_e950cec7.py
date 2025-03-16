# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Automated test generation using Aider with intelligent context management."""

import json
import subprocess
import time
from pathlib import Path


class TestGenerator:
    def __init__(self) -> None:
        self.scripts_dir = Path("scripts")
        self.tests_dir = Path("tests")
        self.coverage_file = Path(".test_coverage.json")
        self.test_plan_file = Path(".test_plan.json")
        self.context_file = Path(".test_context.json")
        self.aider_url = "http://localhost:8000"

    def analyze_coverage(self) -> dict[str, float]:
        """Analyze current test coverage percentage for each script."""
        coverage = {}

        try:
            # Run coverage measurement
            subprocess.run(
                [
                    "coverage",
                    "run",
                    "-m",
                    "pytest",
                    "--cov=scripts",
                    "--cov-report=json",
                ],
                check=True,
            )

            # Load coverage data
            with open(".coverage.json") as f:
                cov_data = json.load(f)

            # Process coverage data
            for file_data in cov_data["files"].values():
                filename = Path(file_data["filename"]).name
                if filename.startswith(("test_", "_")):
                    continue

                total_lines = file_data["summary"]["num_statements"]
                covered_lines = file_data["summary"]["covered_lines"]
                coverage[filename] = (
                    covered_lines / total_lines if total_lines > 0 else 0
                )

        except subprocess.CalledProcessError:
            # If no tests exist, assume 0% coverage for all files
            for script in self.scripts_dir.glob("*.py"):
                if not script.name.startswith("_"):
                    coverage[script.name] = 0.0

        return coverage

    def generate_test_plan(self) -> list[dict]:
        """Generate a prioritized test plan based on coverage analysis."""
        coverage = self.analyze_coverage()
        scripts = sorted(self.scripts_dir.glob("*.py"))

        plan = []
        for script in scripts:
            if script.name.startswith("_"):
                continue

            plan.append(
                {
                    "script": script.name,
                    "test_file": f"test_{script.name}",
                    "priority": 1 - coverage.get(script.name, 0),
                    "status": "pending",
                    "last_attempt": None,
                    "attempts": 0,
                },
            )

        # Sort by priority (lowest coverage first)
        plan.sort(key=lambda x: x["priority"], reverse=True)
        return plan

    def save_context(self, context: dict) -> None:
        """Save current context to file."""
        with open(self.context_file, "w") as f:
            json.dump(context, f, indent=2)

    def load_context(self) -> dict:
        """Load context from file."""
        if self.context_file.exists():
            with open(self.context_file) as f:
                return json.load(f)
        return {}

    def call_aider(self, prompt: str, files: list[str]) -> str:
        """Call Aider API to generate test code."""
        from aider.coders import Coder
        from aider.io import InputOutput
        from aider.models import Model

        try:
            # Set up Aider with non-interactive mode
            io = InputOutput(yes=True)
            model = Model("gpt-4-turbo")

            # Create coder instance with the target files
            coder = Coder.create(
                main_model=model,
                fnames=files,
                io=io,
                auto_commits=False,
                dirty_commits=False,
            )

            # Execute the prompt
            coder.run(prompt)

            # Get the modified content of the test file
            test_file = f"test_{Path(files[0]).name}"
            if test_file in coder.abs_fnames:
                return coder.abs_fnames[test_file].content
            return ""

        except Exception:
            return ""

    def generate_test_file(self, script_name: str, test_file: str) -> bool:
        """Generate tests for a specific script."""
        prompt = f"""
        Write comprehensive unit tests for {script_name} following these guidelines:
        1. Cover all public functions and classes
        2. Include edge cases and error conditions
        3. Use pytest style
        4. Include docstrings explaining each test
        5. Use fixtures where appropriate
        6. Include type hints
        7. Follow project's coding standards

        Create the tests in a new file called {test_file} in the tests directory.
        """

        files = [str(self.scripts_dir / script_name)]
        response = self.call_aider(prompt, files)

        if not response:
            return False

        # Save generated test file
        test_path = self.tests_dir / test_file
        test_path.write_text(response)
        return True

    def run(self) -> None:
        """Main execution loop for test generation."""
        context = self.load_context()

        if not context:
            # First run - generate initial plan
            plan = self.generate_test_plan()
            context = {
                "plan": plan,
                "current_index": 0,
                "start_time": time.time(),
                "stats": {"completed": 0, "failed": 0, "remaining": len(plan)},
            }
            self.save_context(context)

        while context["current_index"] < len(context["plan"]):
            current_item = context["plan"][context["current_index"]]

            if current_item["status"] == "pending":
                try:
                    success = self.generate_test_file(
                        current_item["script"],
                        current_item["test_file"],
                    )

                    if success:
                        current_item["status"] = "completed"
                        context["stats"]["completed"] += 1
                    else:
                        current_item["status"] = "failed"
                        context["stats"]["failed"] += 1

                    context["stats"]["remaining"] -= 1
                    current_item["last_attempt"] = time.time()
                    current_item["attempts"] += 1

                    self.save_context(context)

                except Exception:
                    current_item["status"] = "error"
                    self.save_context(context)
                    continue

            context["current_index"] += 1


if __name__ == "__main__":
    generator = TestGenerator()
    generator.run()
