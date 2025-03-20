import logging
from pathlib import Path
from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.core.db.utils import create_table, execute_query
from dewey.llm.llm_utils import call_llm

class CompanyAnalysisManager(BaseScript):
    """
    Manages the analysis of company data, including fetching, processing, and storing information.
    """

    def __init__(self, config_section: Optional[str] = "company_analysis") -> None:
        """
        Initializes the CompanyAnalysisManager.

        Args:
            config_section: The section in the dewey.yaml configuration file to use for this script.
        """
        super().__init__(
            name="CompanyAnalysisManager",
            description="Manages company data analysis.",
            config_section=config_section,
            requires_db=True,
            enable_llm=True,
        )

    def run(self) -> None:
        """
        Executes the company analysis process.
        """
        try:
            self.logger.info("Starting company analysis process.")
            company_ticker = self.get_config_value("company_ticker")
            if not company_ticker:
                raise ValueError("Company ticker not found in configuration.")

            analysis_results = self._analyze_company(company_ticker)
            self._store_analysis_results(company_ticker, analysis_results)
            self.logger.info("Company analysis process completed successfully.")

        except Exception as e:
            self.logger.error(f"An error occurred during company analysis: {e}", exc_info=True)
            raise

    def _analyze_company(self, company_ticker: str) -> Dict[str, Any]:
        """
        Analyzes a company using LLM and other tools.

        Args:
            company_ticker: The ticker symbol of the company to analyze.

        Returns:
            A dictionary containing the analysis results.

        Raises:
            Exception: If there is an error during the analysis process.
        """
        try:
            self.logger.info(f"Analyzing company: {company_ticker}")
            prompt = f"Analyze the company with ticker {company_ticker}."
            llm_response = call_llm(prompt, llm_client=self.llm_client)

            if not llm_response:
                raise ValueError("LLM analysis failed to return a response.")

            analysis_results = {"llm_analysis": llm_response}
            self.logger.info(f"Company analysis completed for: {company_ticker}")
            return analysis_results

        except Exception as e:
            self.logger.error(f"Error analyzing company {company_ticker}: {e}", exc_info=True)
            raise

    def _store_analysis_results(self, company_ticker: str, analysis_results: Dict[str, Any]) -> None:
        """
        Stores the analysis results in the database.

        Args:
            company_ticker: The ticker symbol of the company.
            analysis_results: A dictionary containing the analysis results.

        Raises:
            Exception: If there is an error storing the analysis results in the database.
        """
        try:
            self.logger.info(f"Storing analysis results for: {company_ticker}")
            table_name = "company_analysis_results"
            schema = {
                "company_ticker": "TEXT",
                "analysis_data": "JSON",
            }

            create_table(self.db_conn, table_name, schema)

            insert_query = f"""
                INSERT INTO {table_name} (company_ticker, analysis_data)
                VALUES (?, ?)
            """
            values = (company_ticker, str(analysis_results))
            execute_query(self.db_conn, insert_query, values)

            self.logger.info(f"Analysis results stored successfully for: {company_ticker}")

        except Exception as e:
            self.logger.error(f"Error storing analysis results for {company_ticker}: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    manager = CompanyAnalysisManager()
    manager.execute()
