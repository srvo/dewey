import json
from pathlib import Path
from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript


class ResearchOutputHandler(BaseScript):
    """Handler for research output.
    
    This class handles the output of research tasks, providing methods for 
    saving and loading research results, as well as writing output to
    specified locations.
    """

    def __init__(self, output_dir: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize the output handler.

        Args:
            output_dir: Directory for output files
            **kwargs: Additional keyword arguments
        """
        super().__init__(config_section="research_output", **kwargs)
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else Path(self.get_config_value("output_dir", "output"))
        )

    def run(self) -> None:
        """Run the research output handler.
        
        This method handles core output operations if configured to run 
        independently, but most functionality is typically accessed via
        the specific methods.
        
        Raises:
            ValueError: If a required configuration value is missing.
        """
        self.logger.info("Running ResearchOutputHandler...")
        
        try:
            output_path = self.get_config_value("output_path")
            if not output_path:
                self.logger.info("No output_path specified in config, using default operations")
                return

            # Process data as configured
            output_data = self.get_config_value("output_data", {})
            self.write_output(output_path, output_data)
        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")

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
            
    def write_output(self, output_path: str, data: Dict[str, Any]) -> None:
        """Writes the output data to the specified path.

        Args:
            output_path: The path to write the output data.
            data: The data to write.
        """
        output_file = Path(output_path)
        
        # Ensure parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write data to the file
            if output_file.suffix.lower() == '.json':
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
            else:
                # Default to string representation for other file types
                with open(output_file, "w") as f:
                    f.write(str(data))
                    
            self.logger.info(f"Output written to: {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write output to {output_path}: {e}")
            raise
