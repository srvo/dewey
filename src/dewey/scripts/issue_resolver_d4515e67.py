# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from scripts.code_analyzer import FixPlan, Issue


def main() -> None:
    """Main entry point with error handling."""
    try:

        # Load analysis report
        report_file = Path(".code-analysis.json")
        if not report_file.exists():
            subprocess.run([sys.executable, "scripts/code_analyzer.py"], check=False)

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

            for issue in plan.issues:

                if issue.fixable:
                    subprocess.run(plan.fix_command.split(), check=False)
                else:
                    pass

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
