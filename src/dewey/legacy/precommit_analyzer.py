
# Refactored from: precommit_analyzer
# Date: 2025-03-16T16:19:11.507735
# Refactor Version: 1.0
# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path


def call_aider(prompt: str, file_path: str) -> str:
    """Call aider via command line and capture output."""
    try:
        result = subprocess.run(
            ["aider", "--message", prompt, file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


class Status(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()
    FAILED = auto()


@dataclass
class FixTask:
    file: str
    issues: list[str]
    status: Status
    fixable: bool = True  # Add this
    start_time: datetime = None
    end_time: datetime = None
    fix_template: str | None = None
    fix_command: str | None = None

    def to_dict(self):
        return {
            "file": self.file,
            "issues": self.issues,
            "status": self.status.name,
            "fixable": self.fixable,  # Include fixable in dict
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "fix_template": self.fix_template,
            "fix_command": self.fix_command,
        }


@dataclass
class FixPlan:
    tool: str
    issues: list[FixTask]
    timestamp: str
    fix_command: str

    def to_dict(self):
        return {
            "tool": self.tool,
            "issues": [task.to_dict() for task in self.issues],
            "timestamp": self.timestamp,
            "fix_command": self.fix_command,
        }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Analyze and fix pre-commit issues")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix fixable issues",
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    return parser.parse_args()


class PrecommitAnalyzer:
    """Analyzes and fixes pre-commit hook issues."""

    def parse_ruff_issues(self, json_file: Path) -> dict[str, list[dict]]:
        """Parse ruff JSON output into a dictionary grouped by file."""
        if not json_file.exists():
            return {}

        try:
            with open(json_file) as f:
                data = json.load(f)

            # Group issues by file
            issues = {}
            for item in data:
                file_path = item["filename"]
                if file_path not in issues:
                    issues[file_path] = []
                issues[file_path].append(item)

            return issues
        except Exception as e:
            self.print_status(f"Error parsing ruff output: {e!s}", Status.FAILED)
            return {}

    def parse_flake8_output(self, json_file: Path) -> dict[str, list[dict]]:
        """Parse flake8 JSON output."""
        if not json_file.exists():
            return {}

        try:
            with open(json_file) as f:
                data = json.load(f)

            # Convert to same format as ruff output
            issues = {}
            for item in data:
                file_path = item["filename"]
                if file_path not in issues:
                    issues[file_path] = []
                issues[file_path].append(item)

            return issues
        except Exception as e:
            self.print_status(f"Error parsing flake8 output: {e!s}", Status.FAILED)
            return {}

    def parse_format_output(self, json_file: Path) -> dict[str, list[dict]]:
        """Parse ruff format output."""
        if not json_file.exists():
            return {}

        try:
            with open(json_file) as f:
                data = f.read()

            # Handle diff format
            issues = {}
            for line in data.splitlines():
                if line.startswith("---"):
                    file_path = line.split()[1]
                    issues[file_path] = [
                        {
                            "filename": file_path,
                            "code": "FMT",
                            "message": "File needs formatting",
                            "fixable": True,
                        },
                    ]

            return issues
        except Exception as e:
            self.print_status(f"Error parsing format output: {e!s}", Status.FAILED)
            return {}

    def __init__(self, fix=False, verbose=False) -> None:
        """Initialize the PrecommitAnalyzer with default settings.

        Creates necessary directories and initializes AIDER components.

        Args:
        ----
            fix (bool): Whether to automatically fix issues
            verbose (bool): Whether to show detailed output

        """
        self.fix = fix
        self.verbose = verbose
        self.report_file = Path(".precommit-fixes.json")
        self.fix_dir = Path(".precommit-fixes")
        self.template_dir = self.fix_dir / "templates"
        self.current_fix_index = 0
        self.total_issues = 0
        self.completed_issues = 0
        self.failed_issues = 0

        # Configure tools with fix commands
        self.tools = {
            "ruff_lint": {
                "command": ["ruff", "check", ".", "--output-format=json"],
                "fix_command": ["ruff", "check", "--fix"],
                "parser": self.parse_ruff_issues,
                "output_type": "json",
            },
            "flake8": {
                "command": ["flake8", "--format=json", "--statistics", "--count"],
                "fix_command": ["autopep8", "--in-place"],
                "parser": self.parse_flake8_output,
                "output_type": "json",
            },
            "ruff_format": {
                "command": ["ruff", "format", "--diff"],
                "fix_command": ["ruff", "format"],
                "parser": self.parse_format_output,
                "output_type": "text",
            },
        }

        # Initialize directories
        self._init_directories()

    def _init_directories(self) -> None:
        """Initialize required directories."""
        self.fix_dir.mkdir(exist_ok=True)
        self.template_dir.mkdir(exist_ok=True)

    def print_status(self, message: str, status: Status = Status.PENDING) -> None:
        """Print colored status messages."""

    def print_progress(self) -> None:
        """Show progress bar and statistics."""
        if self.total_issues == 0:
            return

        progress = self.completed_issues / self.total_issues
        bar_length = 40
        filled = int(bar_length * progress)
        "█" * filled + "-" * (bar_length - filled)

    def run_ruff(self) -> Path:
        """Run ruff and write output to JSON file."""
        output_file = self.fix_dir / "ruff_output.json"
        self.print_status(
            f"Running ruff checks (output to {output_file})...",
            Status.IN_PROGRESS,
        )

        try:
            cmd = ["ruff", "check", ".", "--output-format=json"]
            if self.fix:
                cmd.append("--fix")

            with open(output_file, "w") as f:
                subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=False)

            return output_file
        except Exception as e:
            self.print_status(f"Ruff checks failed: {e!s}", Status.FAILED)
            return None

    def parse_ruff_issues(self, json_file: Path) -> dict[str, list[dict]]:
        """Parse ruff JSON output."""
        if not json_file.exists():
            return {}

        try:
            with open(json_file) as f:
                # Ruff outputs a list of issues
                issues_list = json.load(f)

                # Convert to dictionary grouped by file
                issues_dict = {}
                for issue in issues_list:
                    file_path = issue["filename"]
                    if file_path not in issues_dict:
                        issues_dict[file_path] = []
                    issues_dict[file_path].append(issue)

                return issues_dict
        except Exception as e:
            self.print_status(f"Error parsing ruff output: {e!s}", Status.FAILED)
            return {}

    def _parse_ruff_output(self, output: str) -> dict[str, list[str]]:
        """Parse ruff output into structured data."""
        issues = {}
        current_file = None

        for line in output.splitlines():
            if line.startswith("Found"):
                continue
            if ":" in line:
                file_path = line.split(":")[0]
                if Path(file_path).exists():
                    current_file = file_path
                    issues[current_file] = []
            if current_file and line.strip():
                issues[current_file].append(line.strip())

        return issues

    def run_precommit(self) -> dict[str, list[str]]:
        """Run pre-commit and capture all failures."""
        self.print_status("Running pre-commit checks...", Status.IN_PROGRESS)
        try:
            result = subprocess.run(
                ["pre-commit", "run", "--all-files", "--show-diff"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.print_status("Pre-commit checks completed", Status.COMPLETE)
            return self._parse_failures(result.stdout)
        except subprocess.CalledProcessError as e:
            self.print_status(f"Pre-commit checks failed: {e.stderr}", Status.FAILED)
            return self._parse_failures(e.stdout)

    def _parse_failures(self, output: str) -> dict[str, list[str]]:
        """Parse pre-commit output into structured data."""
        failures = {}
        current_file = None

        for line in output.splitlines():
            if line.startswith(
                ("Trim trailing whitespace", "Check for merge conflicts"),
            ):
                current_file = None
            elif line.startswith("Fixing"):
                current_file = line.split()[-1]
                failures[current_file] = []
            elif current_file and line.strip():
                failures[current_file].append(line.strip())

        return failures

    def create_fix_plan(self, tool_name: str, issues: dict[str, list[dict]]) -> FixPlan:
        """Create structured fix plan from tool issues."""
        self.print_status(f"Creating fix plan for {tool_name}...", Status.IN_PROGRESS)

        # Convert issues to FixTasks
        fix_tasks = []
        for file_path, file_issues in issues.items():
            task = FixTask(
                file=file_path,
                issues=[
                    f"{i.get('code', 'UNKNOWN')}: {i.get('message', 'No message')}"
                    for i in file_issues
                ],
                status=Status.PENDING,
                fixable=True,  # Set fixable status
                fix_template=None,
                fix_command=" ".join(self.tools[tool_name]["fix_command"]),
            )
            fix_tasks.append(task)
            self.total_issues += len(task.issues)

        self.print_status(
            f"Created fix plan with {len(fix_tasks)} tasks",
            Status.COMPLETE,
        )
        return FixPlan(
            tool=tool_name,
            issues=fix_tasks,
            timestamp=datetime.now().isoformat(),
            fix_command=" ".join(self.tools[tool_name]["fix_command"]),
        )

    def save_fix_plan(self, plans: list[FixPlan]) -> None:
        """Save fix plan to file."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "plans": [plan.to_dict() for plan in plans],
        }
        with open(self.report_file, "w") as f:
            json.dump(report, f, indent=2)

    def load_fix_plan(self) -> list[FixTask]:
        """Load fix plan from file."""
        if not self.report_file.exists():
            return []

        with open(self.report_file) as f:
            plan_data = json.load(f)

        return [
            FixTask(
                file=task["file"],
                issues=task["issues"],
                status=Status[task["status"]],
                start_time=(
                    datetime.fromisoformat(task["start_time"])
                    if task["start_time"]
                    else None
                ),
                end_time=(
                    datetime.fromisoformat(task["end_time"])
                    if task["end_time"]
                    else None
                ),
                fix_template=task.get("fix_template"),
            )
            for task in plan_data
        ]

    def get_fix_template(self, issue_type: str) -> str | None:
        """Get fix template for a specific issue type."""
        template_file = self.template_dir / f"{issue_type}.py"
        if template_file.exists():
            with open(template_file) as f:
                return f.read()
        return None

    def update_fix_template(self, issue_type: str, template: str) -> None:
        """Update or create a fix template."""
        template_file = self.template_dir / f"{issue_type}.py"
        with open(template_file, "w") as f:
            f.write(template)

    def generate_fix_template(self, issue_type: str) -> str | None:
        """Generate a fix template for a specific issue type using AIDER.

        Args:
        ----
            issue_type (str): The type of issue to generate a template for.

        Returns:
        -------
            Optional[str]: The generated template code, or None if generation failed.

        The method:
        1. Creates a temporary Python file
        2. Uses AIDER command line to generate code
        3. Captures the generated code
        4. Cleans up temporary resources

        """
        """Generate a fix template using aider command line"""
        try:
            # Create temporary file
            temp_file = self.fix_dir / "temp_template.py"
            temp_file.touch()

            # Generate the prompt
            prompt = f"""
            Create a Python function to fix {issue_type} issues in code.
            The function should:
            1. Take a file path as input
            2. Return True if successful, False otherwise
            3. Handle errors gracefully
            4. Include type hints
            5. Include docstring
            6. Follow PEP 8 style
            7. Be compatible with Python 3.8+
            8. Use pathlib for file operations
            9. Include proper logging
            10. Handle edge cases

            The function should be named 'fix_issue' and have the following signature:
            def fix_issue(file_path: str) -> bool:
                ...
            """

            # Call aider via command line
            call_aider(prompt, str(temp_file))

            # Read the generated template
            if temp_file.exists():
                with open(temp_file) as f:
                    return f.read()
            return None

        except Exception as e:
            self.print_status(f"Error generating template: {e!s}", Status.FAILED)
            return None
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def refresh_fix_templates(self) -> None:
        """Refresh all fix templates using AIDER.

        This method:
        1. Identifies all unique issue types from the current fix plan
        2. Generates or updates templates for each issue type
        3. Stores templates in the template directory
        4. Provides detailed status updates
        """
        """Refresh fix templates using AIDER"""
        self.print_status("Refreshing fix templates...", Status.IN_PROGRESS)

        # Get all unique issue types from current plan
        plan = self.load_fix_plan()
        issue_types = set()
        for task in plan:
            for issue in task.issues:
                issue_type = issue.split(":")[0].strip()
                issue_types.add(issue_type)

        # Generate/update templates for each issue type
        for issue_type in issue_types:
            self.print_status(
                f"Generating template for {issue_type}...",
                Status.IN_PROGRESS,
            )

            template = self.generate_fix_template(issue_type)

            if template:
                self.update_fix_template(issue_type, template)
                self.print_status(f"Template for {issue_type} updated", Status.COMPLETE)
            else:
                self.print_status(
                    f"Failed to generate template for {issue_type}",
                    Status.FAILED,
                )

    def apply_fix(self, file_path: str, issue: str, template: str) -> bool:
        """Apply a fix using the provided template."""
        try:
            # Create temporary module with the fix function
            temp_module = self.fix_dir / "temp_fix.py"
            with open(temp_module, "w") as f:
                f.write(template)

            # Import and execute the fix
            spec = importlib.util.spec_from_file_location("temp_fix", temp_module)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Call the fix function
            return module.fix_issue(file_path)

        except Exception as e:
            self.print_status(f"Error applying fix: {e!s}", Status.FAILED)
            return False
        finally:
            if temp_module.exists():
                temp_module.unlink()

    def process_fix_task(self, task: FixTask) -> bool:
        """Process a single fix task using dynamic templates."""
        self.print_status(
            f"Processing {task.file} ({len(task.issues)} issues)",
            Status.IN_PROGRESS,
        )
        task.start_time = datetime.now()

        try:
            for issue in task.issues:
                self.print_status(f"Fixing: {issue}", Status.IN_PROGRESS)

                # Get issue type and template
                issue_type = issue.split(":")[0].strip()
                template = self.get_fix_template(issue_type)

                if not template:
                    self.print_status(
                        f"No template found for {issue_type}",
                        Status.FAILED,
                    )
                    self.failed_issues += 1
                    continue

                # Apply the fix
                if self.apply_fix(task.file, issue, template):
                    self.completed_issues += 1
                    self.print_progress()
                else:
                    self.failed_issues += 1
                    self.print_status(f"Failed to fix {issue}", Status.FAILED)

            task.status = Status.COMPLETE
            task.end_time = datetime.now()
            duration = (task.end_time - task.start_time).total_seconds()
            self.print_status(
                f"Completed {task.file} in {duration:.2f}s",
                Status.COMPLETE,
            )
            return True

        except Exception as e:
            self.failed_issues += len(task.issues) - (
                self.completed_issues % len(task.issues)
            )
            task.status = Status.FAILED
            task.end_time = datetime.now()
            self.print_status(f"Failed to process {task.file}: {e!s}", Status.FAILED)
            return False

    def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        self.print_status("Cleaning up temporary files...", Status.IN_PROGRESS)

        # Remove all tool output files
        for tool in self.tools:
            output_file = self.fix_dir / f"{tool}_output.json"
            if output_file.exists():
                try:
                    output_file.unlink()
                    self.print_status(f"Removed {tool} output", Status.COMPLETE)
                except Exception as e:
                    self.print_status(
                        f"Error removing {tool} output: {e!s}",
                        Status.FAILED,
                    )

        # Clean up any other temporary files
        for temp_file in self.fix_dir.glob("temp_*"):
            try:
                temp_file.unlink()
            except Exception:
                continue

    def process_tasks(self, plans: list[FixPlan]) -> None:
        """Process all fix tasks from the plans."""
        self.print_status("Processing fix tasks...", Status.IN_PROGRESS)

        for plan in plans:
            self.print_status(f"Processing {plan.tool} issues...", Status.IN_PROGRESS)

            # Run the fix command if there are fixable issues
            if any(issue.fixable for issue in plan.issues):
                self.print_status(
                    f"Running fix command: {plan.fix_command}",
                    Status.IN_PROGRESS,
                )
                try:
                    subprocess.run(plan.fix_command.split(), check=True)
                    self.print_status(
                        f"Fix command completed for {plan.tool}",
                        Status.COMPLETE,
                    )
                except subprocess.CalledProcessError as e:
                    self.print_status(
                        f"Fix command failed for {plan.tool}: {e!s}",
                        Status.FAILED,
                    )

            # Process individual tasks
            for task in plan.issues:
                if task.fixable:
                    self.process_fix_task(task)
                else:
                    self.print_status(
                        f"Skipping manual fix for {task.file}: {task.issues[0]}",
                        Status.IN_PROGRESS,
                    )

        self.print_status("All tasks processed", Status.COMPLETE)

    def process_fix_task(self, task: FixTask) -> bool:
        """Process a single fix task using dynamic templates."""
        self.print_status(
            f"Processing {task.file} ({len(task.issues)} issues)",
            Status.IN_PROGRESS,
        )
        task.start_time = datetime.now()

        try:
            for issue in task.issues:
                self.print_status(f"Fixing: {issue}", Status.IN_PROGRESS)

                # Get issue type and template
                issue_type = issue.split(":")[0].strip()
                template = self.get_fix_template(issue_type)

                if not template:
                    self.print_status(
                        f"No template found for {issue_type}",
                        Status.FAILED,
                    )
                    self.failed_issues += 1
                    continue

                # Apply the fix
                if self.apply_fix(task.file, issue, template):
                    self.completed_issues += 1
                    self.print_progress()
                else:
                    self.failed_issues += 1
                    self.print_status(f"Failed to fix {issue}", Status.FAILED)

            task.status = Status.COMPLETE
            task.end_time = datetime.now()
            duration = (task.end_time - task.start_time).total_seconds()
            self.print_status(
                f"Completed {task.file} in {duration:.2f}s",
                Status.COMPLETE,
            )
            return True

        except Exception as e:
            self.failed_issues += len(task.issues) - (
                self.completed_issues % len(task.issues)
            )
            task.status = Status.FAILED
            task.end_time = datetime.now()
            self.print_status(f"Failed to process {task.file}: {e!s}", Status.FAILED)
            return False

    def run(self) -> None:
        """Main execution flow with JSON-based processing."""
        try:
            plans = []

            # Run all configured tools
            for tool_name, config in self.tools.items():
                self.print_status(f"Running {tool_name}...", Status.IN_PROGRESS)

                # Run the tool
                output = self.run_tool(tool_name)
                if not output:
                    continue

                # Process the output
                issues = config["parser"](output)
                if not issues:
                    self.print_status(
                        f"No issues found with {tool_name}",
                        Status.COMPLETE,
                    )
                    continue

                # Create fix plan
                plan = self.create_fix_plan(tool_name, issues)
                plans.append(plan)
                self.print_status(
                    f"Found {len(issues)} issues with {tool_name}",
                    Status.COMPLETE,
                )

            if not plans:
                self.print_status("No issues found in any checks!", Status.COMPLETE)
                return

            # Save and process fix plans
            self.save_fix_plan(plans)
            self.process_tasks(plans)

            # Generate final report
            self.generate_report(plans)
            self.print_summary(plans)

        except Exception as e:
            self.print_status(f"\nError during analysis: {e!s}", Status.FAILED)
            sys.exit(1)
        finally:
            self.cleanup()

    def run_tool(self, tool_name: str) -> Path | None:
        """Run a configured tool and return its output file."""
        if tool_name not in self.tools:
            self.print_status(f"Unknown tool: {tool_name}", Status.FAILED)
            return None

        config = self.tools[tool_name]
        output_file = self.fix_dir / f"{tool_name}_output.json"

        try:
            # Run the tool and capture output
            result = subprocess.run(
                config["command"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Handle flake8 specifically
            if tool_name == "flake8":
                # Flake8 outputs JSON lines format
                try:
                    # Parse each line as JSON and combine into array
                    issues = []
                    for line in result.stdout.splitlines():
                        if line.strip():  # Skip empty lines
                            issues.append(json.loads(line))

                    # Write combined JSON array to file
                    with open(output_file, "w") as f:
                        json.dump(issues, f)
                    return output_file
                except json.JSONDecodeError as e:
                    self.print_status(f"Flake8 JSON decode error: {e!s}", Status.FAILED)
                    return None

            # Handle other tools
            if config.get("output_type") == "json":
                json_data = json.loads(result.stdout)
                with open(output_file, "w") as f:
                    json.dump(json_data, f)
            else:
                with open(output_file, "w") as f:
                    f.write(result.stdout)

            return output_file
        except Exception as e:
            self.print_status(f"{tool_name} failed: {e!s}", Status.FAILED)
            return None


def main() -> None:
    """Main entry point for the pre-commit analyzer script."""
    analyzer = PrecommitAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
