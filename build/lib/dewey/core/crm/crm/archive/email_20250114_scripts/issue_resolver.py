#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from scripts.code_analyzer import FixPlan, Issue


def main():
    """Main entry point with error handling."""
    try:
        print("Running issue resolver...")

        # Load analysis report
        report_file = Path(".code-analysis.json")
        if not report_file.exists():
            print("No analysis report found. Running analysis first...")
            subprocess.run([sys.executable, "scripts/code_analyzer.py"])

        with open(report_file) as f:
            report = json.load(f)

        # Process each fix plan
        for plan_data in report["plans"]:
            plan = FixPlan(
                tool=plan_data["tool"],
                issues=[Issue(**issue) for issue in plan_data["issues"]],
                timestamp=plan_data["timestamp"],
                fix_command=plan_data["fix_command"],
            )

            print(f"\nProcessing {plan.tool} issues:")
            for issue in plan.issues:
                print(f"  {issue.file}:{issue.line}:{issue.column}")
                print(f"    {issue.code} - {issue.message}")

                if issue.fixable:
                    print("    Applying automatic fix...")
                    subprocess.run(plan.fix_command.split())
                else:
                    print("    Manual fix required")

    except Exception as e:
        print(f"\nError during issue resolution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
