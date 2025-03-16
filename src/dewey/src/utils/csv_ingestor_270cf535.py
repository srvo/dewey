```python
import argparse
import csv
import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db.schema import AttioContact


class CSVIngestor:
    """
    Ingests CSV data into a PostgreSQL database using SQLAlchemy.
    """

    def __init__(self) -> None:
        """
        Initializes the CSVIngestor with database connection and field mapping.
        """
        load_dotenv()
        db_url = os.getenv("DB_URL")
        if not db_url:
            raise ValueError(
                "DB_URL environment variable not set.\n"
                "1. Check your.env file exists\n"
                "2. Verify it contains: DB_URL=postgresql://user:pass@host/dbname"
            )

        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)

        self.field_map: Dict[str, str] = {
            "Record ID": "record_id",
            "Record": "record",
            "Connection strength": "connection_strength",
            "Last email interaction > When": "last_email_interaction_when",
            "Last calendar interaction > When": "last_calendar_interaction_when",
            "Name": "name",
            "Email addresses": "email_addresses",
            "Description": "description",
            "Company": "company",
            "Job title": "job_title",
            "Phone numbers": "phone_numbers",
            "Primary location > State": "primary_location_state",
            "Facebook": "facebook",
            "Instagram": "instagram",
            "LinkedIn": "linkedin",
            "Twitter": "twitter",
            "# of Accounts": "number_of_accounts",
            "Cash": "cash",
            "Balance": "balance",
        }

    def _validate_row(self, row: Dict[str, str]) -> bool:
        """
        Validates required fields in a CSV row.

        Args:
            row (Dict[str, str]): A dictionary representing a row from the CSV file.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = [
            "Record ID",  # Maps to record_id (primary key)
            "Last email interaction > When",  # Required by DB schema
        ]

        for csv_field in required_fields:
            if not row.get(csv_field, "").strip():
                self.logger.warning(f"Missing required field: {csv_field}")
                return False
        return True

    def _map_row(self, row: Dict[str, Any]) -> AttioContact | None:
        """
        Maps a CSV row to an AttioContact instance.

        Args:
            row (Dict[str, Any]): A dictionary representing a row from the CSV file.

        Returns:
            AttioContact | None: An AttioContact instance if mapping is successful, None otherwise.
        """
        if not self._validate_row(row):
            return None

        mapped: Dict[str, Any] = {}
        for csv_field, model_field in self.field_map.items():
            value = row.get(csv_field, "").strip()

            # Handle empty datetime specifically
            if csv_field == "Last email interaction > When" and not value:
                value = "1970-01-01"  # Default fallback for required datetime

            col_obj = getattr(AttioContact, model_field)

            if hasattr(col_obj.type, "length"):
                value = value[: col_obj.type.length]

            mapped[model_field] = value or None

        mapped["raw_data"] = {k: v or None for k, v in row.items()}

        try:
            return AttioContact(**mapped)
        except TypeError as e:
            self.logger.error(f"Mapping error: {str(e)}")
            return None

    def ingest_file(self, file_path: str, batch_size: int = 1000) -> dict:
        """
        Ingests data from a CSV file into the database.

        Args:
            file_path (str): The path to the CSV file.
            batch_size (int): The number of rows to process in each batch.

        Returns:
            dict: A dictionary containing summary statistics of the ingestion process.
        """
        stats = {"total": 0, "upserted": 0, "errors": 0, "mapping_failures": 0}

        with self.Session() as session, open(file_path, "r") as f:
            reader = csv.DictReader(f)
            batch = []

            for row in reader:
                stats["total"] += 1
                try:
                    contact = self._map_row(row)
                    if not contact:
                        stats["mapping_failures"] += 1
                        continue

                    batch.append(contact)
                    if len(batch) >= batch_size:
                        for contact in batch:
                            session.merge(contact)
                        session.commit()
                        stats["upserted"] += len(batch)
                        batch = []

                except Exception as e:
                    stats["errors"] += 1
                    self.logger.error(f"Row error: {str(e)}", exc_info=True)
                    session.rollback()
                    batch = []

            if batch:
                for contact in batch:
                    session.merge(contact)
                session.commit()
                stats["upserted"] += len(batch)

        return stats


def configure_logging() -> None:
    """
    Configures logging for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("ingestion.log")],
    )


def main() -> None:
    """
    Main function to parse arguments and start the CSV ingestion process.
    """
    load_dotenv()
    configure_logging()
    parser = argparse.ArgumentParser(description="CSV to PostgreSQL ingestor")
    parser.add_argument("--file", required=True, help="Path to CSV file")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Rows per batch (default: 5000)",
    )
    args = parser.parse_args()

    start_time = time.time()
    ingestor = CSVIngestor()
    stats = ingestor.ingest_file(args.file, args.batch_size)

    print("\nIngestion Summary:")
    print(f"Total Records Processed: {stats['total']}")
    print(f"Successfully Upserted: {stats['upserted']}")
    print(f"Mapping Failures: {stats['mapping_failures']}")
    print(f"Errors Encountered: {stats['errors']}")
    print(f"Records/s: {(stats['total'] / (time.time() - start_time)):.1f}")


if __name__ == "__main__":
    main()
```
