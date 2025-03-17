#!/usr/bin/env python3
"""Script to format files into Obsidian documentation."""

import argparse
import logging
import sys
from pathlib import Path

from file_analyzer.obsidian_formatter import ObsidianFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Format files into Obsidian documentation.')
    parser.add_argument('input_dir', help='Directory containing files to process')
    parser.add_argument('output_dir', help='Directory to write Obsidian docs to')
    parser.add_argument('--analysis-dir', help='Directory containing file analysis results')
    
    args = parser.parse_args()
    
    try:
        input_path = Path(args.input_dir)
        output_path = Path(args.output_dir)
        
        if not input_path.exists():
            logger.error(f"Input directory does not exist: {input_path}")
            sys.exit(1)
            
        logger.info(f"Processing files from: {input_path}")
        logger.info(f"Writing Obsidian docs to: {output_path}")
        
        if args.analysis_dir:
            logger.info(f"Using analysis data from: {args.analysis_dir}")
            
        formatter = ObsidianFormatter(
            str(input_path),
            analysis_dir=args.analysis_dir
        )
        formatter.create_obsidian_docs(str(output_path))
        
        logger.info("Successfully created Obsidian documentation")
        
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 