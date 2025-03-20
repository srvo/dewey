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
        super().__init__(config_section='research_output')
        self.output_dir = Path(output_dir) if output_dir else Path(
            self.get_config_value('output_dir', 'output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Run the research output handler."""
        self.logger.info("Running ResearchOutputHandler...")

    def save_results(self, results: Dict[str, Any], output_file: Optional[Path] = None) -> None:
        """Save research results to a file.

        Args:
            results: Results to save.
            output_file: Optional output file path.
        """
        if output_file is None:
            output_file = self.output_dir / self.get_config_value('default_output_file', 'results.json')

        # Ensure parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save results as JSON
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        self.logger.info(f"Results saved to {output_file}")

    def load_results(self, input_file: Optional[Path] = None) -> Dict[str, Any]:
        """Load research results from a file.

        Args:
            input_file: Optional input file path.

        Returns:
            Loaded results.
        """
        if input_file is None:
            input_file = self.output_dir / self.get_config_value('default_output_file', 'results.json')

        if not input_file.exists():
            self.logger.warning(f"Input file not found: {input_file}")
            return {}

        # Load results from JSON
        with open(input_file) as f:
            results = json.load(f)
        self.logger.info(f"Results loaded from {input_file}")
        return results
