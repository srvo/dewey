import json
from pathlib import Path
from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript


class ResearchOutputHandler(BaseScript):
    """Handler for research output."""

    def __init__(self, output_dir: Optional[str] = None) -> None:
        """Initialize the output handler.

        Args:
            output_dir: Directory for output files
        """
        super().__init__(config_section="research_output")
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else Path(self.get_config_value("output_dir", "output"))
        )

    def run(self) -> None:
        """Run the research output handler."""
        self.logger.info("Running ResearchOutputHandler...")
        # No core logic here, methods are called externally

    def save_results(
        self, results: Dict[str, Any], output_file: Optional[Path] = None
    ) -> None:
        """Save research results to a file.

        Args:
            results: Results to save.
            output_file: Optional output file path.
        """
        if output_file is None:
            default_output_file = self.get_config_value(
                "default_output_file", "results.json"
            )
            output_file = self.output_dir / default_output_file

        # Ensure parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save results as JSON
        try:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving results to {output_file}: {e}")

    def load_results(self, input_file: Optional[Path] = None) -> Dict[str, Any]:
        """Load research results from a file.

        Args:
            input_file: Optional input file path.

        Returns:
            Loaded results.
        """
        if input_file is None:
            default_output_file = self.get_config_value(
                "default_output_file", "results.json"
            )
            input_file = self.output_dir / default_output_file

        if not input_file.exists():
            self.logger.warning(f"Input file not found: {input_file}")
            return {}

        # Load results from JSON
        try:
            with open(input_file) as f:
                results = json.load(f)
            self.logger.info(f"Results loaded from {input_file}")
            return results
        except Exception as e:
            self.logger.error(f"Error loading results from {input_file}: {e}")
            return {}
