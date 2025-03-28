from pathlib import Path
from datetime import datetime, timedelta
from dewey.core.base_script import BaseScript

class LogCleanup(BaseScript):
    def execute(self):
        """Main execution method for log cleanup."""
        log_dir = Path(self.get_config_value("logging.root_dir", "logs"))
        retention_days = self.get_config_value("logging.retention_days", 3))
        
        self.logger.info(f"Starting log cleanup in {log_dir} (retention: {retention_days} days)")
        self._cleanup_directory(log_dir, retention_days)
        
        # Clean archived logs if configured
        archive_dir = Path(self.get_config_value("logging.archive_dir", "logs/archived"))
        if archive_dir.exists():
            self._cleanup_directory(archive_dir, retention_days)

    def _cleanup_directory(self, directory: Path, retention_days: int):
        """Clean logs in a specific directory."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0
        
        for log_file in directory.rglob("*.log"):
            if log_file.is_file() and self._is_old_file(log_file, cutoff):
                self._safe_delete(log_file)
                deleted += 1
                
        self.logger.info(f"Cleaned {deleted} files from {directory}")

    def _is_old_file(self, file_path: Path, cutoff: datetime) -> bool:
        """Check if a file is older than cutoff."""
        try:
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return file_mtime < cutoff
        except FileNotFoundError:
            return False

    def _safe_delete(self, file_path: Path):
        """Safely delete a file with error handling."""
        try:
            file_path.unlink()
            self.logger.debug(f"Deleted: {file_path}")
        except Exception as e:
            self.logger.error(f"Error deleting {file_path}: {str(e)}")

if __name__ == "__main__":
    LogCleanup().execute()
