from dewey.core.base_script import BaseScript


class Backup(BaseScript):
    """
    Manages database backups.

    This class inherits from BaseScript and provides methods for
    backing up and restoring the database.
    """

    def __init__(self, config_section: str = "backup") -> None:
        """
        Initializes the Backup class.

        Args:
            config_section: The configuration section to use.
        """
        super().__init__(config_section=config_section, requires_db=True)

    def run(self) -> None:
        """
        Runs the database backup process.
        """
        self.logger.info("Starting database backup...")
        backup_location = self.get_config_value("backup_location", "/default/backup/path")
        self.logger.info(f"Backing up to: {backup_location}")
        # Implement backup logic here
        self._backup_database(backup_location)
        self.logger.info("Database backup complete.")

    def restore(self) -> None:
        """
        Restores the database from a backup.
        """
        self.logger.info("Starting database restore...")
        restore_location = self.get_config_value("restore_location", "/default/restore/path")
        self.logger.info(f"Restoring from: {restore_location}")
        # Implement restore logic here
        self._restore_database(restore_location)
        self.logger.info("Database restore complete.")

    def _backup_database(self, backup_location: str) -> None:
        """
        Backs up the database to the specified location.

        Args:
            backup_location: The location to back up the database to.
        """
        try:
            from dewey.core.db.utils import backup_database

            backup_database(self.db_conn, backup_location, self.logger)
        except Exception as e:
            self.logger.error(f"Error backing up database: {e}")
            raise

    def _restore_database(self, restore_location: str) -> None:
        """
        Restores the database from the specified location.

        Args:
            restore_location: The location to restore the database from.
        """
        try:
            from dewey.core.db.utils import restore_database

            restore_database(self.db_conn, restore_location, self.logger)
        except Exception as e:
            self.logger.error(f"Error restoring database: {e}")
            raise
