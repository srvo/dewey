from dewey.core.base_script import BaseScript


class Companies(BaseScript):
    """
    A class for performing company-related research and analysis.
    """

    def __init__(self):
        """
        Initializes the Companies script with configuration and dependencies.
        """
        super().__init__(config_section="companies", requires_db=True, enable_llm=True)

    def run(self) -> None:
        """
        Executes the main logic of the Companies script.

        This method orchestrates the process of researching and analyzing companies,
        including fetching data, performing analysis, and storing results.

        Raises:
            Exception: If any error occurs during the process.
        """
        try:
            self.logger.info("Starting company research and analysis...")

            # Example: Accessing configuration values
            api_url = self.get_config_value("api_url", "https://default-api-url.com")
            self.logger.debug(f"API URL: {api_url}")

            # Example: Database operations (replace with actual logic)
            from dewey.core.db.utils import execute_query
            query = "SELECT * FROM companies LIMIT 10;"
            results = execute_query(self.db_conn, query)
            self.logger.info(f"Fetched {len(results)} companies from the database.")

            # Example: LLM usage (replace with actual logic)
            from dewey.llm.llm_utils import generate_text
            prompt = "Summarize the key activities of a technology company."
            summary = generate_text(self.llm_client, prompt)
            self.logger.info(f"Generated summary: {summary[:50]}...")

            self.logger.info("Company research and analysis completed.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}", exc_info=True)
            raise
