#!/usr/bin/env python3
"""
Example script demonstrating the proper usage of BaseScript.

This script shows how to implement a script that inherits from BaseScript
and follows all the project conventions.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from src.core.base_script import BaseScript


class ExampleScript(BaseScript):
    """Example script that demonstrates BaseScript usage.
    
    This script processes an input file and outputs results to a specified
    location, demonstrating proper command-line argument handling, logging,
    and error handling.
    """
    
    def _add_arguments(self, parser):
        """Add script-specific command-line arguments.
        
        Args:
            parser: ArgumentParser instance to add arguments to
        """
        parser.add_argument('--input', required=True, 
                           help='Path to input file to process')
        parser.add_argument('--output', required=True,
                           help='Path to output file')
        parser.add_argument('--format', choices=['json', 'csv', 'txt'], 
                           default='json', help='Output format')
        
    def setup(self):
        """Set up script resources and validate inputs."""
        super().setup()
        
        # Validate input file exists
        if not os.path.exists(self.args.input):
            raise FileNotFoundError(f"Input file not found: {self.args.input}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(self.args.output)
        if output_dir and not os.path.exists(output_dir):
            self.logger.info(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # Initialize any needed resources
        self.temp_files = []
        self.processed_data = None
    
    def run(self):
        """Run the main script logic.
        
        This method implements the core functionality of the script.
        """
        self.logger.info(f"Processing input file: {self.args.input}")
        
        try:
            # Load input data
            data = self._load_data(self.args.input)
            
            # Process the data
            self.processed_data = self._process_data(data)
            
            # Write the output
            self._write_output(self.processed_data, self.args.output, self.args.format)
            
            self.logger.info(f"Successfully processed data and wrote output to {self.args.output}")
        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}")
            raise
    
    def cleanup(self):
        """Perform cleanup operations after script execution."""
        super().cleanup()
        
        # Clean up any temporary files
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                self.logger.debug(f"Removing temporary file: {temp_file}")
                os.remove(temp_file)
    
    def _load_data(self, input_path: str) -> Dict[str, Any]:
        """Load data from the input file.
        
        Args:
            input_path: Path to the input file
            
        Returns:
            Loaded data as a dictionary
        """
        self.logger.debug(f"Loading data from {input_path}")
        
        with open(input_path, 'r') as file:
            if input_path.endswith('.json'):
                return json.load(file)
            else:
                # Simple example - just read lines
                return {"lines": file.readlines()}
    
    def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Processed data dictionary
        """
        self.logger.debug("Processing data")
        
        # This is a placeholder for actual data processing
        result = {
            "original_data": data,
            "summary": {
                "num_items": len(data),
                "processed_timestamp": self._get_timestamp()
            }
        }
        
        return result
    
    def _write_output(self, data: Dict[str, Any], output_path: str, format_type: str) -> None:
        """Write the processed data to the output file.
        
        Args:
            data: Processed data dictionary
            output_path: Path to the output file
            format_type: Format type (json, csv, or txt)
        """
        self.logger.debug(f"Writing output to {output_path} in {format_type} format")
        
        with open(output_path, 'w') as file:
            if format_type == 'json':
                json.dump(data, file, indent=2)
            elif format_type == 'csv':
                # Simple CSV example
                for key, value in data.items():
                    file.write(f"{key},{value}\n")
            else:  # txt format
                file.write(str(data))
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp.
        
        Returns:
            Current timestamp as a string
        """
        import datetime
        return datetime.datetime.now().isoformat()


def main():
    """Main entry point for the script."""
    script = ExampleScript(
        name="ExampleScript",
        description="Example script that demonstrates BaseScript usage"
    )
    return script.execute()


if __name__ == "__main__":
    import sys
    sys.exit(main()) 