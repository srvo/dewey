"""Main entry point for transcript analyzer."""
import argparse
import logging
import sys
from pathlib import Path

from .config import Config
from .core import TranscriptAnalyzer

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main entry point."""
    # Set up logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description='Analyze transcripts and generate documentation.')
    parser.add_argument('input_dir', help='Directory containing transcripts to analyze')
    parser.add_argument('output_dir', help='Directory to write analysis results to')
    
    args = parser.parse_args()
    
    try:
        # Initialize config with command line arguments
        config = Config()
        config.input_dir = Path(args.input_dir)
        config.output_dir = Path(args.output_dir)
        
        # Validate configuration
        config.validate()
        
        # Initialize and run analyzer
        analyzer = TranscriptAnalyzer(config)
        analyzer.process_directory(config.input_dir)
        
        logger.info("Analysis complete")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 