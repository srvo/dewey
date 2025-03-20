from dewey.core.base_script import BaseScript


class CompanyResearch(BaseScript):
    """
    Base class for company research modules within Dewey.

    This class provides a standardized structure for company research scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(
        self,
        config_section: str = "company_research",
        requires_db: bool = True,
        enable_llm: bool = True,
    ) -> None:
        """
        Initializes the CompanyResearch module.

        Args:
            config_section (str): Section in dewey.yaml to load for this script. Defaults to "company_research".
            requires_db (bool): Whether this script requires database access. Defaults to True.
            enable_llm (bool): Whether this script requires LLM access. Defaults to True.

        """
        super().__init__(
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )
        self.name = "CompanyResearch"
        self.description = "Base class for company research scripts."

    def run(self) -> None:
        """
        Executes the primary logic of the company research script.

        This method should be overridden by subclasses to implement specific
        research tasks.

        Raises:
            Exception: If there is an error during company research.
        """
        self.logger.info("Starting company research...")
        try:
            # Example of accessing a configuration value
            example_config_value = self.get_config_value(
                "example_config_key", "default_value"
            )
            self.logger.debug(f"Example config value: {example_config_value}")

            # Example of using the database connection
            if self.db_conn:
                self.logger.info("Successfully connected to the database.")
                # Example query (replace with your actual query)
                # Assuming you have a table named 'companies'
                # and you want to fetch all company names
                try:
                    with self.db_conn.cursor() as cursor:
                        cursor.execute("SELECT * FROM companies LIMIT 10;")
                        results = cursor.fetchall()
                        self.logger.info(f"Example query results: {results}")
                except Exception as e:
                    self.logger.error(f"Error executing database query: {e}")
            else:
                self.logger.warning("Database connection is not available.")

            # Example of using the LLM client
            if self.llm_client:
                self.logger.info("Successfully initialized LLM client.")
                # Example LLM call (replace with your actual prompt)
                try:
                    response = self.llm_client.generate(
                        prompt="Tell me about the company Apple."
                    )
                    self.logger.info(f"LLM response: {response}")
                except Exception as e:
                    self.logger.error(f"Error calling LLM: {e}")
            else:
                self.logger.warning("LLM client is not available.")

            self.logger.info("Company research completed.")

        except Exception as e:
            self.logger.error(
                f"An error occurred during company research: {e}", exc_info=True
            )
            raise


if __name__ == "__main__":
    # Example usage (this would typically be called from a workflow)
    research_module = CompanyResearch()
    research_module.execute()
