from dewey.core.base_script import BaseScript


class GmailService(BaseScript):
    """
    A service class for interacting with the Gmail API.

    This class handles authentication, email retrieval, and other Gmail-related
    operations.
    """

    def __init__(self):
        """
        Initializes the GmailService with necessary configurations and credentials.
        """
        super().__init__(config_section="gmail", requires_db=False, enable_llm=False)

    def run(self):
        """
        Executes the main logic of the Gmail service.

        This method should be implemented to perform specific tasks, such as
        fetching emails, processing them, and storing the results.

        Raises:
            NotImplementedError: If the run method is not implemented in a subclass.
        """
        self.logger.info("Gmail service started.")
        # Implement your Gmail service logic here
        self.logger.info("Gmail service completed.")
