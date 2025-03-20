from dewey.core.base_script import BaseScript


class EmailDataGenerator(BaseScript):
    """
    Generates data related to emails.

    This class inherits from BaseScript and provides methods for generating
    email-related data.
    """

    def __init__(self):
        """
        Initializes the EmailDataGenerator.

        Calls the superclass constructor with the appropriate configuration
        section and requirements.
        """
        super().__init__(config_section="email_data_generator", requires_db=True, enable_llm=True)

    def run(self) -> None:
        """
        Runs the email data generation process.

        This method contains the core logic for generating email data.
        """
        self.logger.info("Starting email data generation...")

        # Example usage of configuration values
        num_emails = self.get_config_value("num_emails", 10)
        self.logger.info(f"Generating {num_emails} emails.")

        # Example usage of database connection
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")  # Example query
                result = cursor.fetchone()
                self.logger.info(f"Database connection test: {result}")
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")

        # Example usage of LLM client
        try:
            response = self.llm_client.generate_text("Write a short email subject.")
            self.logger.info(f"LLM response: {response}")
        except Exception as e:
            self.logger.error(f"Error using LLM: {e}")

        self.logger.info("Email data generation completed.")
