#!/usr/bin/env python3

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List


class Status(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()
    FAILED = auto()


@dataclass
class Issue:
    file: str
    line: int
    column: int
    code: str
    message: str
    fixable: bool


@dataclass
class FixPlan:
    tool: str
    issues: List[Issue]
    timestamp: str
    fix_command: str


class CodeAnalyzer:
    def __init__(self):
        self.report_file = Path(".code-analysis.json")
        self.tools = {
            "ruff_lint": {
                "command": ["ruff", "check", ".", "--output-format=json"],
                "fix_command": ["ruff", "check", "--fix"],
            },
            "ruff_format": {
                "command": ["ruff", "format", "--diff"],
                "fix_command": ["ruff", "format"],
            },
            "flake8": {
                "command": ["flake8", "--format=json", "--statistics", "--count"],
                "fix_command": ["autopep8", "--in-place"],
            }
        }

    def run_tool(self, tool: str) -> List[Dict]:
        """Run a code analysis tool and return its output."""
        try:
            result = subprocess.run(
                self.tools[tool]["command"], capture_output=True, text=True, check=True
            )
            if tool == "ruff":
                return json.loads(result.stdout)
            return result.stdout.splitlines()
        except subprocess.CalledProcessError as e:
            print(f"Error running {tool}: {e.stderr}")
            return []

    def parse_format_output(self, output: str) -> List[Issue]:
        """Parse ruff format output into issues."""
        issues = []
        for line in output.splitlines():
            if line.startswith("---"):
                file_path = line.split()[1]
                issues.append(Issue(
                    file=file_path,
                    line=0,
                    column=0,
                    code="FMT",
                    message="File needs formatting",
                    fixable=True
                ))
        return issues

    def parse_ruff_issues(self, data: List[Dict]) -> List[Issue]:
        """Parse Ruff's JSON output into Issue objects."""
        issues = []
        for item in data:
            issues.append(
                Issue(
                    file=item["filename"],
                    line=item["location"]["row"],
                    column=item["location"]["column"],
                    code=item["code"],
                    message=item["message"],
                    fixable=item.get("fix", {}).get("applicable", False),
                )
            )
        return issues

    def parse_flake8_output(self, output: str) -> List[Issue]:
        """Parse flake8 JSON output into issues."""
        try:
            data = json.loads(output)
            return [
                Issue(
                    file=item["filename"],
                    line=item["line_number"],
                    column=item["column_number"],
                    code=item["code"],
                    message=item["text"],
                    fixable="E" in item["code"] or "W" in item["code"],
                )
                for item in data
            ]
        except json.JSONDecodeError:
            return []

    def create_fix_plan(self, tool: str, issues: List[Issue]) -> FixPlan:
        """Create a fix plan for the identified issues."""
        return FixPlan(
            tool=tool,
            issues=issues,
            timestamp=datetime.now().isoformat(),
            fix_command=" ".join(self.tools[tool]["fix_command"]),
        )

    def generate_report(self, plans: List[FixPlan]):
        """Generate a JSON report of all fix plans."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "plans": [plan.to_dict() for plan in plans]
        }

        with open(self.report_file, "w") as f:
            json.dump(report, f, indent=2)

    def print_summary(self, plans: List[FixPlan]):
        """Print a human-readable summary of issues."""
        print("\nCode Analysis Summary:")
        print("=" * 40)
        
        total_issues = 0
        fixable_issues = 0
        issue_counts = {}

        for plan in plans:
            print(f"\n{plan.tool.upper()} Issues:")
            print("-" * 40)

            if not plan.issues:
                print("  No issues found!")
                continue

            # Count issues by type
            tool_counts = {}
            for issue in plan.issues:
                total_issues += 1
                if issue.fixable:
                    fixable_issues += 1
                    
                issue_type = issue.code.split(".")[0]  # Get main category
                tool_counts[issue_type] = tool_counts.get(issue_type, 0) + 1
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

                if plan.tool == "ruff_format":
                    print(f"  {issue.file} needs formatting")
                else:
                    status = "FIXABLE" if issue.fixable else "MANUAL FIX REQUIRED"
                    print(f"  {issue.file}:{issue.line}:{issue.column}")
                    print(f"    {issue.code} - {issue.message}")
                    print(f"    Status: {status}")

            # Print tool-specific statistics
            print("\n  Statistics:")
            for issue_type, count in tool_counts.items():
                print(f"    {issue_type}: {count} issues")

        # Print overall statistics
        print("\nSummary Statistics:")
        print(f"- Total issues found: {total_issues}")
        print(f"- Fixable issues: {fixable_issues}")
        print(f"- Manual fixes required: {total_issues - fixable_issues}")
        
        print("\nIssue Breakdown:")
        for issue_type, count in sorted(issue_counts.items()):
            print(f"  {issue_type}: {count} issues")

        print("\nTo fix issues, run:")
        for plan in plans:
            if plan.issues:
                print(f"  {plan.fix_command}")
        
        if fixable_issues > 0:
            print("\nYou can fix all fixable issues by running:")
            print("  poetry run pre-commit run --all-files")

    def install_missing_dependencies(self):
        """Install missing dependencies found during checks."""
        print("Checking for missing dependencies...")
        
        try:
            # Run poetry check
            result = subprocess.run(
                ["poetry", "check"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                # Parse output for missing dependencies
                missing = []
                for line in result.stderr.splitlines():
                    if "not found" in line:
                        package = line.split("'")[1]
                        missing.append(package)
                
                if missing:
                    print(f"Found {len(missing)} missing dependencies")
                    for package in missing:
                        print(f"Installing {package}...")
                        subprocess.run(
                            ["poetry", "add", package],
                            check=True
                        )
                    print("Dependencies installed")
                else:
                    print("No missing dependencies found")
                    
        except Exception as e:
            print(f"Error installing dependencies: {str(e)}")

    def run(self):
        """Main analysis workflow."""
        plans = []

        # First ensure dependencies are installed
        self.install_missing_dependencies()

        # Run all checks
        checks = [
            ("ruff_lint", self.parse_ruff_issues),
            ("ruff_format", self.parse_format_output),
            ("flake8", self.parse_flake8_output),
        ]

        for tool_name, parser in checks:
            self.print_status(f"Running {tool_name}...", Status.IN_PROGRESS)
            output = self.run_tool(tool_name)
            if output:
                issues = parser(output)
                if issues:
                    plans.append(self.create_fix_plan(tool_name, issues))
                    self.print_status(f"Found {len(issues)} issues with {tool_name}", Status.COMPLETE)
                else:
                    self.print_status(f"No issues found with {tool_name}", Status.COMPLETE)

        # Generate report and summary
        if plans:
            self.generate_report(plans)
            self.print_summary(plans)
        else:
            self.print_status("No issues found in any checks!", Status.COMPLETE)


def main():
    """Entry point for standalone execution."""
    try:
        # Run analysis
        analyzer = CodeAnalyzer()
        analyzer.run()

        # Automatically apply fixes
        print("\nApplying automatic fixes...")
        subprocess.run(["ruff", "check", "--fix"])
        subprocess.run(["ruff", "format"])

        print("\nAll fixes applied successfully!")

    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
