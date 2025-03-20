from dewey.core.base_script import BaseScript
import logging


class AdminTasks(BaseScript):
    """
    A class for performing administrative tasks, such as database
    maintenance and user management.
    """

    def __init__(self):
        """
        Initializes the AdminTasks script.
        """
        super().__init__(config_section="admin", requires_db=True)
        self.logger = logging.getLogger(__name__)  # Get logger instance

    def run(self):
        """
        Executes the administrative tasks.
        """
        self.logger.info("Starting administrative tasks...")
        try:
            self.perform_database_maintenance()
            self.logger.info("Administrative tasks completed.")
        except Exception as e:
            self.logger.error(f"Error during administrative tasks: {e}")
            raise

    def perform_database_maintenance(self):
        """
        Performs database maintenance tasks, such as vacuuming and
        analyzing tables.
        """
        try:
            self.logger.info("Performing database maintenance...")
            with self.db_conn.cursor() as cursor:
                cursor.execute("VACUUM;")
                self.logger.info("VACUUM completed.")
                cursor.execute("ANALYZE;")
                self.logger.info("ANALYZE completed.")
            self.db_conn.commit()
            self.logger.info("Database maintenance completed.")
        except Exception as e:
            self.logger.error(f"Error performing database maintenance: {e}")
            self.db_conn.rollback()  # Rollback in case of error
            raise

    def add_user(self, username, password):
        """
        Adds a new user to the system.

        Args:
            username (str): The username of the new user.
            password (str): The password of the new user.

        Raises:
            ValueError: If the username already exists.
        """
        try:
            self.logger.info(f"Adding user {username}...")
            with self.db_conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s);",
                    (username, password),
                )
            self.db_conn.commit()
            self.logger.info(f"User {username} added successfully.")
        except Exception as e:
            self.logger.error(f"Error adding user {username}: {e}")
            self.db_conn.rollback()  # Rollback in case of error
            raise
