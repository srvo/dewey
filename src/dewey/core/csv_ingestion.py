#!/usr/bin/env python3
"""
CSV Ingestion Module for Dewey

This module provides robust CSV ingestion capabilities with:
- Automatic encoding detection
- Smart data type inference
- Schema validation and mapping
- Error handling and logging
- Progress tracking
"""

import os
import csv
import chardet
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from tqdm import tqdm

from dewey.core.base_script import BaseScript
from dewey.core.engines import MotherDuckEngine

# Configure logging
logger = logging.getLogger(__name__)

class CSVIngestionError(Exception):
    """Base exception for CSV ingestion errors."""
    pass

class CSVIngestionScript(BaseScript):
    """Script for ingesting CSV files into MotherDuck."""
    
    def __init__(self):
        """Initialize the CSV ingestion script."""
        super().__init__(
            name="csv_ingestion",
            description="Ingest CSV files into MotherDuck with smart type inference"
        )
        self.processed_files: Dict[str, Dict] = {}
        self.error_files: Dict[str, str] = {}
    
    def setup_argparse(self):
        """Set up argument parsing."""
        parser = super().setup_argparse()
        parser.add_argument(
            "--input-dir",
            type=str,
            default="input_data/csv_files",
            help="Directory containing CSV files"
        )
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Recursively process subdirectories"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analyze files without ingesting"
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip files that have already been processed"
        )
        return parser
    
    def _detect_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Detect CSV file information including encoding and structure.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Dict containing file metadata
        """
        # Read file sample for detection
        sample_size = min(32 * 1024, os.path.getsize(file_path))  # 32KB or file size
        with open(file_path, 'rb') as f:
            raw_sample = f.read(sample_size)
        
        # Detect encoding
        encoding_result = chardet.detect(raw_sample)
        encoding = encoding_result['encoding'] or 'utf-8'
        
        # Try reading with detected encoding
        try:
            df = pd.read_csv(file_path, encoding=encoding, nrows=5)
            has_header = True
        except pd.errors.EmptyDataError:
            return {
                'empty': True,
                'encoding': encoding,
                'error': 'File is empty'
            }
        except Exception as e:
            # Try without header
            try:
                df = pd.read_csv(file_path, encoding=encoding, header=None, nrows=5)
                has_header = False
            except Exception as e2:
                return {
                    'error': f"Failed to read file: {str(e2)}",
                    'encoding': encoding
                }
        
        # Get basic stats
        try:
            total_rows = sum(1 for _ in open(file_path, encoding=encoding)) - (1 if has_header else 0)
        except Exception:
            total_rows = None
        
        # Analyze columns
        columns = df.columns.tolist()
        dtypes = df.dtypes.to_dict()
        
        return {
            'encoding': encoding,
            'has_header': has_header,
            'columns': columns,
            'dtypes': {str(k): str(v) for k, v in dtypes.items()},
            'total_rows': total_rows,
            'sample_rows': df.head().to_dict('records')
        }
    
    def _generate_table_name(self, file_path: Path) -> str:
        """Generate a suitable table name from the file path.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Clean table name
        """
        # Get base name without extension
        base_name = file_path.stem.lower()
        
        # Clean up name
        base_name = ''.join(c if c.isalnum() else '_' for c in base_name)
        base_name = base_name.strip('_')
        
        # Remove date patterns
        import re
        base_name = re.sub(r'_\d{6}_\d{6}', '', base_name)
        base_name = re.sub(r'_\d{8}', '', base_name)
        base_name = re.sub(r'_\d{14}', '', base_name)
        
        # Add csv prefix if needed
        if not base_name.startswith('csv_'):
            base_name = f"csv_{base_name}"
        
        return base_name
    
    def _ingest_file(self, file_path: Path, table_name: str, file_info: Dict[str, Any]) -> bool:
        """Ingest a CSV file into MotherDuck.
        
        Args:
            file_path: Path to the CSV file
            table_name: Name for the destination table
            file_info: File metadata from _detect_file_info
            
        Returns:
            bool indicating success
        """
        try:
            # Prepare SQL for table creation
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS 
                SELECT * FROM read_csv_auto(
                    '{file_path}',
                    header={str(file_info['has_header']).lower()},
                    filename=true,
                    all_varchar=false,
                    sample_size=1000,
                    auto_detect=true
                )
            """
            
            # Execute creation
            self.db_engine.execute(create_sql)
            
            # Verify row count
            if file_info['total_rows']:
                actual_count = self.db_engine.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                if actual_count == 0:
                    raise CSVIngestionError(f"Table was created but contains no rows")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {str(e)}")
            return False
    
    def _save_metadata(self, file_path: Path, table_name: str, file_info: Dict[str, Any], success: bool):
        """Save metadata about the processed file.
        
        Args:
            file_path: Path to the CSV file
            table_name: Name of the created table
            file_info: File metadata
            success: Whether ingestion was successful
        """
        metadata_path = file_path.with_suffix('.csv.metadata')
        metadata = {
            'file_path': str(file_path),
            'table_name': table_name,
            'processed_at': datetime.now().isoformat(),
            'success': success,
            'info': file_info
        }
        
        try:
            import yaml
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata, f)
        except Exception as e:
            logger.warning(f"Failed to save metadata for {file_path}: {str(e)}")
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            bool indicating success
        """
        try:
            # Skip if already processed
            if self.args.skip_existing and file_path.with_suffix('.csv.metadata').exists():
                logger.info(f"Skipping previously processed file: {file_path}")
                return True
            
            # Detect file information
            file_info = self._detect_file_info(file_path)
            if 'error' in file_info:
                self.error_files[str(file_path)] = file_info['error']
                return False
            
            # Generate table name
            table_name = self._generate_table_name(file_path)
            
            # Store processing info
            self.processed_files[str(file_path)] = {
                'table_name': table_name,
                'info': file_info
            }
            
            # If dry run, stop here
            if self.args.dry_run:
                return True
            
            # Ingest file
            success = self._ingest_file(file_path, table_name, file_info)
            
            # Save metadata
            self._save_metadata(file_path, table_name, file_info, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            self.error_files[str(file_path)] = str(e)
            return False
    
    def run(self):
        """Run the CSV ingestion script."""
        input_dir = Path(self.args.input_dir)
        if not input_dir.exists():
            raise CSVIngestionError(f"Input directory not found: {input_dir}")
        
        # Find all CSV files
        pattern = '**/*.csv' if self.args.recursive else '*.csv'
        csv_files = list(input_dir.glob(pattern))
        
        if not csv_files:
            logger.info(f"No CSV files found in {input_dir}")
            return
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        # Process files with progress bar
        with tqdm(total=len(csv_files), desc="Processing CSV files") as pbar:
            for file_path in csv_files:
                success = self.process_file(file_path)
                if success:
                    pbar.set_description(f"Processed {file_path.name}")
                else:
                    pbar.set_description(f"Failed {file_path.name}")
                pbar.update(1)
        
        # Print summary
        print("\nProcessing Summary:")
        print("=" * 80)
        print(f"Total files: {len(csv_files)}")
        print(f"Successfully processed: {len(self.processed_files)}")
        print(f"Failed: {len(self.error_files)}")
        
        if self.error_files:
            print("\nFailed Files:")
            for file_path, error in self.error_files.items():
                print(f"- {file_path}: {error}")
        
        if not self.args.dry_run:
            print("\nCreated Tables:")
            for file_info in self.processed_files.values():
                print(f"- {file_info['table_name']}")

def main():
    """Main entry point."""
    CSVIngestionScript().main()

if __name__ == '__main__':
    main() 