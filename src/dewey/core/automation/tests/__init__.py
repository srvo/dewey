import argparse
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class LLMClientInterface(ABC):
    """An interface for LLM clients."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Generates text based on the given prompt."""
        pass


class DataAnalysisScript(BaseScript):
    """A script to fetch data from a database, analyze it with an LLM,
    and log the results.
    """

    def __init__(
        self,
        db_connection: DatabaseConnection | None = None,
        llm_client: LLMClientInterface | None = None,
    ) -> None:
        """Initializes the DataAnalysisScript with configurations for database
        and LLM.
        """
        super().__init__(
            name="DataAnalysisScript",
            description="Fetches data, analyzes it with an LLM, and logs results.",
            config_section="data_analysis",
            requires_db=True,
            enable_llm=True,
        )
        self.db_connection = db_connection or DatabaseConnection(self.config)
        self.llm_client = llm_client or LLMClient()

    def _fetch_data(self) -> dict[str, Any]:
        """Fetches data from the database.

        Returns:
            A dictionary containing the fetched data.

        Raises:
            Exception: If there is an error fetching data from the database.

        """
        try:
            with self.db_connection as db_conn:
                # Assuming you have a table named 'data_table'
                result = db_conn.execute("SELECT * FROM example_table")
                data = {"data": result.fetchall()}  # Fetch all rows
                return data
        except Exception:
            raise

    def fetch_data_from_db(self) -> dict[str, Any]:
        """Fetches data from the database and logs the action.

        Returns:
            A dictionary containing the fetched data.

        Raises:
            Exception: If there is an error fetching data from the database.

        """
        self.logger.info("Fetching data from database...")
        try:
            data = self._fetch_data()
            return data
        except Exception as e:
            self.logger.error(f"Error fetching data from database: {e}")
            raise

    def _analyze_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analyzes the given data using an LLM.

        Args:
            data: A dictionary containing the data to be analyzed.

        Returns:
            A dictionary containing the analysis results.

        Raises:
            ValueError: If the LLM client is not initialized.
            Exception: If there is an error analyzing data with the LLM.

        """
        if not self.llm_client:
            raise ValueError("LLM client is not initialized.")

        try:
            prompt = f"Analyze this data: {data}"
            analysis_result = self.llm_client.generate_text(prompt)
            analysis = {"analysis": analysis_result}
            return analysis
        except Exception:
            raise

    def analyze_data_with_llm(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analyzes the given data using an LLM and logs the action.

        Args:
            data: A dictionary containing the data to be analyzed.

        Returns:
            A dictionary containing the analysis results.

        Raises:
            Exception: If there is an error analyzing data with the LLM.

        """
        self.logger.info("Analyzing data with LLM...")
        try:
            analysis = self._analyze_data(data)
            return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing data with LLM: {e}")
            raise

    def execute(self) -> None:
        """Executes the data analysis script.

        This method orchestrates the fetching of data from the database,
        analyzing it using a language model, and logging the analysis results.
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

    def run(self) -> None:
        """Runs the data analysis script."""
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
        """Set up command line arguments.

        Returns:
            An argument parser configured with common options.

        """
        parser = super().setup_argparse()
        parser.add_argument("--input", help="Input data")
        return parser


def main() -> None:
    """Main function to execute the DataAnalysisScript."""
    script = DataAnalysisScript()
    script.execute()


if __name__ == "__main__":
    main()
