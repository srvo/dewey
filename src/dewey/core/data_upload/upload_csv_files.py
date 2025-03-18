#!/usr/bin/env python3

from dewey.core.base_script import BaseScript
from dewey.core.data_upload import DataUploader
from pathlib import Path
import sys

class CSVUploadScript(BaseScript):
    def __init__(self):
        super().__init__(
            name="csv_upload_script",
            description="Upload CSV files to MotherDuck"
        )
        self._uploader = None

    def setup_argparse(self):
        parser = super().setup_argparse()
        parser.add_argument(
            "--input_dir",
            type=str,
            required=True,
            help="Directory containing CSV files"
        )
        parser.add_argument(
            "--target_db",
            type=str,
            default="dewey",
            help="Target database name"
        )
        parser.add_argument(
            "--dedup_strategy",
            choices=["update", "replace", "skip", "version"],
            default="update",
            help="Deduplication strategy"
        )
        return parser

    def initialize(self):
        self._uploader = DataUploader(self.args.target_db)
        self.logger.info(f"Connected to database: {self.args.target_db}")

    def run(self):
        input_dir = Path(self.args.input_dir).expanduser()
        if not input_dir.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")

        csv_files = list(input_dir.glob("*.csv"))
        total_files = len(csv_files)
        self.logger.info(f"Found {total_files} CSV files")

        success_count = 0
        for i, file_path in enumerate(csv_files, 1):
            try:
                self.logger.info(f"Processing file {i}/{total_files}: {file_path.name}")
                self._uploader.upload_file(
                    str(file_path),
                    dedup_strategy=self.args.dedup_strategy
                )
                success_count += 1
                self.logger.info(f"Successfully uploaded {file_path.name}")
            except Exception as e:
                self.logger.error(f"Failed to upload {file_path.name}: {str(e)}")

        self.logger.info(f"\nUpload Summary:")
        self.logger.info(f"Total files: {total_files}")
        self.logger.info(f"Successfully uploaded: {success_count}")
        self.logger.info(f"Failed: {total_files - success_count}")

    def cleanup(self):
        if self._uploader:
            self._uploader.close()

if __name__ == "__main__":
    CSVUploadScript().main() 