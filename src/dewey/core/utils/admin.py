from dewey.core.base_script import BaseScript
import logging
import psycopg2


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
        except psycopg2.Error as e:
            self.logger.error(f"Database error during administrative tasks: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during administrative tasks: {e}")
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
        except psycopg2.Error as e:
            self.logger.error(f"Database error performing database maintenance: {e}")
            self.db_conn.rollback()  # Rollback in case of error
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error performing database maintenance: {e}")
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
                # Check if the users table exists
                cursor.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users');"
                )
                table_exists = cursor.fetchone()[0]
                if not table_exists:
                    self.logger.error("The 'users' table does not exist.")
                    raise ValueError("The 'users' table does not exist.")

                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s);",
                    (username, password),
                )
            self.db_conn.commit()
            self.logger.info(f"User {username} added successfully.")
        except psycopg2.Error as e:
            self.logger.error(f"Database error adding user {username}: {e}")
            self.db_conn.rollback()  # Rollback in case of error
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error adding user {username}: {e}")
            self.db_conn.rollback()  # Rollback in case of error
            raise
