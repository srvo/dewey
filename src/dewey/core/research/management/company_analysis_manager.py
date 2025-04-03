from typing import Any, Dict, Optional
import json

from dewey.core.base_script import BaseScript
from dewey.llm.litellm_utils import quick_completion


class CompanyAnalysisManager(BaseScript):
    """Manages the analysis of company data, including fetching, processing, and storing information."""

    def __init__(self, config_section: str | None = "company_analysis") -> None:
        """Initializes the CompanyAnalysisManager.

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
        """Executes the company analysis process."""
        try:
            self.logger.info("Starting company analysis process.")
            company_ticker = self.get_config_value("company_ticker")
            if not company_ticker:
                raise ValueError("Company ticker not found in configuration.")

            analysis_results = self._analyze_company(company_ticker)
            self._store_analysis_results(company_ticker, analysis_results)
            self.logger.info("Company analysis process completed successfully.")

        except Exception as e:
            self.logger.error(
                f"An error occurred during company analysis: {e}", exc_info=True
            )
            raise

    def _analyze_company(self, company_ticker: str) -> dict[str, Any]:
        """Analyzes a company using LLM and other tools.

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
            llm_response = quick_completion(prompt, llm_client=self.llm_client)

            if not llm_response:
                raise ValueError("LLM analysis failed to return a response.")

            analysis_results = {"llm_analysis": llm_response}
            self.logger.info(f"Company analysis completed for: {company_ticker}")
            return analysis_results

        except Exception as e:
            self.logger.error(
                f"Error analyzing company {company_ticker}: {e}", exc_info=True
            )
            raise

    def _store_analysis_results(
        self, company_ticker: str, analysis_results: dict[str, Any]
    ) -> None:
        """Stores the analysis results in the database."""
        if not self.db_conn:
            self.logger.error("Database connection not available for storing results.")
            return

        try:
            self.logger.info(f"Storing analysis results for: {company_ticker}")
            table_name = "company_analysis_results"
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                company_ticker TEXT PRIMARY KEY,
                analysis_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
            self.db_conn.execute(create_table_sql)

            insert_query = f"""
                INSERT OR REPLACE INTO {table_name} (company_ticker, analysis_data)
                VALUES (?, ?)
            """
            values = (company_ticker, json.dumps(analysis_results))
            self.db_conn.execute(insert_query, values)
            self.db_conn.commit()

            self.logger.info(
                f"Analysis results stored successfully for: {company_ticker}"
            )

        except Exception as e:
            self.logger.error(
                f"Error storing analysis results for {company_ticker}: {e}",
                exc_info=True,
            )


if __name__ == "__main__":
    manager = CompanyAnalysisManager()
    manager.execute()
