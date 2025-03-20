import argparse
import logging
from typing import Any, Dict

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class DataAnalysisScript(BaseScript):
    """
    A script to fetch data from a database, analyze it with an LLM,
    and log the results.
    """

    def __init__(self) -> None:
        """
        Initializes the DataAnalysisScript with configurations for database
        and LLM.
        """
        super().__init__(
            name="DataAnalysisScript",
            description="Fetches data, analyzes it with an LLM, and logs results.",
            config_section="data_analysis",
            requires_db=True,
            enable_llm=True,
        )

    def fetch_data_from_db(self) -> Dict[str, Any]:
        """
        Fetches data from the database.

        Returns:
            A dictionary containing the fetched data.

        Raises:
            Exception: If there is an error fetching data from the database.
        """
        self.logger.info("Fetching data from database...")
        try:
            with DatabaseConnection(self.config) as db_conn:
                # Assuming you have a table named 'data_table'
                result = db_conn.execute("SELECT * FROM example_table")
                data = {"data": result.fetchall()}  # Fetch all rows
                return data
        except Exception as e:
            self.logger.error(f"Error fetching data from database: {e}")
            raise

    def analyze_data_with_llm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the given data using an LLM.

        Args:
            data: A dictionary containing the data to be analyzed.

        Returns:
            A dictionary containing the analysis results.

        Raises:
            Exception: If there is an error analyzing data with the LLM.
        """
        self.logger.info("Analyzing data with LLM...")
        try:
            if not self.llm_client:
                raise ValueError("LLM client is not initialized.")

            prompt = f"Analyze this data: {data}"
            analysis_result = self.llm_client.generate_text(prompt)
            analysis = {"analysis": analysis_result}
            return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing data with LLM: {e}")
            raise

    def run(self) -> None:
        """
        Runs the data analysis script.
        """
        try:
            # Fetch data
            data = self.fetch_data_from_db()

            # Analyze data
            analysis = self.analyze_data_with_llm(data)

            self.logger.info(f"Analysis: {analysis}")
            self.logger.info("Script finished.")

        except Exception as e:
            self.logger.error(f"Script failed: {e}")

    def setup_argparse(self) -> argparse.ArgumentParser:
        """
        Set up command line arguments.

        Returns:
            An argument parser configured with common options.
        """
        parser = super().setup_argparse()
        parser.add_argument("--input", help="Input data")
        return parser


def main() -> None:
    """
    Main function to execute the DataAnalysisScript.
    """
    script = DataAnalysisScript()
    script.execute()


if __name__ == "__main__":
    main()
