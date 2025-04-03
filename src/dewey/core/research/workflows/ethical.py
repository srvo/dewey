#!/usr/bin/env python3
"""Ethical analysis workflow for research."""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from ..base_workflow import BaseWorkflow
from ..engines import BaseEngine
from ...engines.deepseek import DeepSeekEngine
from tests.dewey.core.research.analysis.test_workflow_integration import (
    ResearchOutputHandler,
)


class EthicalAnalysisWorkflow(BaseScript, BaseWorkflow):
    """Workflow for analyzing companies from an ethical perspective."""

    def __init__(
        self,
        data_dir: Union[str, Path],
        search_engine: Optional[BaseEngine] = None,
        analysis_engine: Optional[BaseEngine] = None,
        output_handler: Optional[ResearchOutputHandler] = None,
    ) -> None:
        """Initialize the workflow.

        Args:
            data_dir: Directory for data files.
            search_engine: Optional search engine (defaults to DeepSeekEngine).
            analysis_engine: Optional analysis engine (defaults to DeepSeekEngine).
            output_handler: Optional output handler.

        """
        super().__init__(
            name="EthicalAnalysisWorkflow",
            description="Workflow for analyzing companies from an ethical perspective.",
            config_section="ethical_analysis",
            requires_db=True,
            enable_llm=True,
        )
        self.data_dir = Path(data_dir)
        self.search_engine = search_engine or DeepSeekEngine()
        self.analysis_engine = analysis_engine or DeepSeekEngine()
        self.output_handler = output_handler or ResearchOutputHandler(
            str(self.data_dir)
        )
        self.engine = self.analysis_engine  # For compatibility with test_init_templates
        self.logger = logging.getLogger(__name__)
        self.setup_database()

        # Add templates to analysis engine
        if self.analysis_engine:
            self.analysis_engine.add_template(
                "ethical_analysis",
                """Analyze the ethical implications of {company_name}'s business practices based on the following information:

{search_results}

Please provide:
1. A summary of key ethical considerations
2. Potential risks and concerns
3. Notable positive initiatives
4. Areas for improvement
""",
            )

            self.analysis_engine.add_template(
                "risk_analysis",
                """Assess the risks associated with {company_name} based on:

{search_results}

Please identify:
1. Regulatory compliance risks
2. Reputational risks
3. Environmental risks
4. Social impact risks
5. Governance risks
""",
            )

        # Initialize statistics
        self.stats = {
            "companies_processed": 0,
            "total_searches": 0,
            "total_results": 0,
            "total_snippet_words": 0,
            "total_analyses": 0,
            "total_analysis_words": 0,
        }

    def build_query(self, company_data: Dict[str, str]) -> str:
        """Build a search query for a company.

        Args:
            company_data: Dictionary containing company information.

        Returns:
            Search query string.

        """
        query_parts = [
            str(company_data),
            "ethical",
            "ethics",
            "controversy",
            "controversies",
            "violations",
            "sustainability",
            "corporate responsibility",
        ]
        return " ".join(query_parts)

    @staticmethod
    def word_count(text: str) -> int:
        """Count words in text.

        Args:
            text: Text to count words in

        Returns:
            Number of words

        """
        if not text:
            return 0
        return len(text.split())

    def setup_database(self) -> None:
        """Set up the database schema."""
        with get_connection(for_write=True) as conn:
            # Create sequences first
            conn.execute("CREATE SEQUENCE IF NOT EXISTS research_searches_id_seq")
            conn.execute("CREATE SEQUENCE IF NOT EXISTS research_search_results_id_seq")
            conn.execute("CREATE SEQUENCE IF NOT EXISTS research_analyses_id_seq")

            # Create research_searches table
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS research_searches (
                id INTEGER PRIMARY KEY DEFAULT nextval('research_searches_id_seq'), company_name TEXT NOT NULL, query TEXT NOT NULL, num_results INTEGER DEFAULT 0, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # Create research_search_results table
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS research_search_results (
                id INTEGER PRIMARY KEY DEFAULT nextval('research_search_results_id_seq'), search_id INTEGER NOT NULL, title TEXT, link TEXT, snippet TEXT, source TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (search_id) REFERENCES research_searches(id)
            )
            """
            )

            # Create research_analyses table
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS research_analyses (
                id INTEGER PRIMARY KEY DEFAULT nextval('research_analyses_id_seq'), company TEXT NOT NULL, search_id INTEGER NOT NULL, content TEXT, summary TEXT, historical_analysis TEXT, ethical_score FLOAT, risk_level INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (search_id) REFERENCES research_searches(id)
            )
            """
            )

    def analyze_company_profile(self, company: str) -> Optional[Dict[str, Any]]:
        """Analyze a company's ethical profile.

        Args:
            company: The name of the company to analyze.

        Returns:
            A dictionary containing the analysis results, or None if an error occurred.

        """
        try:
            # Search for company information
            search_results = self.search_engine.search(
                f"{company} ethical issues controversies"
            )
            if not search_results:
                return None

            with get_connection(for_write=True) as conn:
                # Insert search into database
                result = conn.execute(
                    """
                    INSERT INTO research_searches (company_name, query, num_results)
                    VALUES (?, ?, ?)
                    RETURNING id
                """,
                    [
                        company,
                        f"{company} ethical issues controversies",
                        len(search_results),
                    ],
                )
                search_id = result.fetchone()[0]

                # Insert search results
                for result in search_results:
                    conn.execute(
                        """
                        INSERT INTO research_search_results
                        (search_id, title, link, snippet, source)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        [
                            search_id,
                            result.get("title", ""),
                            result.get("link", ""),
                            result.get("snippet", ""),
                            result.get("source", ""),
                        ],
                    )

            # Generate analysis using LLM
            prompt = f"""Analyze the ethical profile of {company} based on the following information:

Search Results:
{json.dumps(search_results, indent=2)}

Please provide:
1. A comprehensive analysis of ethical considerations
2. Risk assessment
3. Historical patterns
4. Recommendations"""

            analysis = self.llm.generate_response(prompt)

            with get_connection(for_write=True) as conn:
                # Insert analysis into database
                conn.execute(
                    """
                    INSERT INTO research_analyses
                    (company, search_id, content, summary, historical_analysis, ethical_score, risk_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    [
                        company,
                        search_id,
                        analysis,
                        "",  # summary
                        "",  # historical_analysis
                        0.0,  # ethical_score
                        0,  # risk_level
                    ],
                )

            return {
                "company": company,
                "search_results": search_results,
                "analysis": analysis,
                "historical": "",  # historical
            }

        except Exception as e:
            self.logger.error(f"Error analyzing company {company}: {str(e)}")
            return None

    def execute(self) -> None:
        """Execute the ethical analysis workflow.

        This method orchestrates the ethical analysis process, including
        reading company data, performing searches, analyzing results, and
        saving the output.
        """
        data_dir = str(self.data_dir)
        try:
            results = self.execute(data_dir)  # Call the existing execute method
            self.logger.info(f"Ethical analysis workflow completed. Results: {results}")
        except FileNotFoundError as e:
            self.logger.error(f"Companies file not found: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error during ethical analysis workflow: {e}")
            raise
