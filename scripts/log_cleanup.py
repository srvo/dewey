import re
from datetime import datetime, timedelta
from pathlib import Path

from dewey.core.base_script import BaseScript


class LogCleanup(BaseScript):
    def execute(self):
        """Main execution method for log cleanup."""
        log_config = self.config.get("logging", {})
        retention_days = log_config.get("retention_days", 3)

        # Clean main logs
        main_log_dir = Path(log_config.get("root_dir", "logs"))
        self.logger.info(
            f"Cleaning main logs in {main_log_dir} (retention: {retention_days} days)",
        )
        self._clean_directory(main_log_dir, retention_days)

        # Clean archived logs
        archive_dir = Path(log_config.get("archive_dir", "logs/archived"))
        if archive_dir.exists():
            archive_retention = log_config.get(
                "archive_retention_days", retention_days * 2,
            )
            self.logger.info(
                f"Cleaning archives in {archive_dir} (retention: {archive_retention} days)",
            )
            self._clean_directory(archive_dir, archive_retention)

    def _clean_directory(self, directory: Path, retention_days: int):
        """Clean logs in a directory using multiple cleanup strategies."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0

        # Enhanced pattern to match various timestamp formats
        timestamp_patterns = [
            re.compile(r".*(\d{8})(_\d+)?\.log$"),  # YYYYMMDD with optional suffix
            re.compile(r".*\d{4}-\d{2}-\d{2}.*\.log$"),  # YYYY-MM-DD
            re.compile(r".*\d{8}T\d{6}.*\.log$"),  # ISO format timestamps
        ]

        for log_file in directory.rglob("*.log"):
            if not log_file.is_file():
                continue

            # Try filename-based date detection first
            file_date = self._extract_date_from_name(log_file.name, timestamp_patterns)

            if file_date and file_date < cutoff:
                self._safe_delete(log_file)
                deleted += 1
                continue

            # Fallback to filesystem metadata
            if self._is_old_file(log_file, cutoff):
                self._safe_delete(log_file)
                deleted += 1

        self.logger.info(f"Cleaned {deleted} files from {directory}")

    def _extract_date_from_name(self, filename: str, patterns: list) -> datetime | None:
        """Extract date from filename using multiple patterns."""
        for pattern in patterns:
            match = pattern.search(filename)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    return datetime.strptime(date_str, "%Y%m%d")
                except ValueError:
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        pass
        return None

    def _is_old_file(self, file_path: Path, cutoff: datetime) -> bool:
        """Check if a file is older than cutoff using modification time."""
        try:
            return datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff
        except FileNotFoundError:
            return False

    def _safe_delete(self, file_path: Path):
        """Safely delete a file with error handling."""
        try:
            file_path.unlink()
            self.logger.debug(f"Deleted: {file_path}")
        except Exception as e:
            self.logger.error(f"Error deleting {file_path}: {e!s}")


if __name__ == "__main__":
    LogCleanup().execute()
