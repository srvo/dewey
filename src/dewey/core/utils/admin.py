from dewey.core.base_script import BaseScript


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

    def run(self):
        """
        Executes the administrative tasks.
        """
        self.logger.info("Starting administrative tasks...")
        self.perform_database_maintenance()
        self.logger.info("Administrative tasks completed.")

    def perform_database_maintenance(self):
        """
        Performs database maintenance tasks, such as vacuuming and
        analyzing tables.
        """
        try:
            self.logger.info("Performing database maintenance...")
            with self.db_conn.cursor() as cursor:
                cursor.execute("VACUUM;")
                cursor.execute("ANALYZE;")
            self.db_conn.commit()
            self.logger.info("Database maintenance completed.")
        except Exception as e:
            self.logger.error(f"Error performing database maintenance: {e}")
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
            raise
