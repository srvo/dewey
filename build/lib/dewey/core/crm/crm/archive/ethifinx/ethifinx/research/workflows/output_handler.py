import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ResearchOutputHandler:
    """
    Handles the formatting and saving of research workflow outputs in a standardized format.

    This class provides a consistent way to:
    - Generate metadata for research outputs
    - Format company analysis results
    - Save combined results to JSON files

    Output Format:
    {
        "meta": {
            "timestamp": "ISO-8601 timestamp",
            "version": "1.0",
            "type": "ethical_analysis"
        },
        "companies": [
            {
                "company_name": "Company name",
                "symbol": "Stock symbol",
                "primary_category": "Industry category",
                "current_criteria": "Analysis criteria",
                "analysis": {
                    "historical": { ... analysis results ... },
                    "evidence": {
                        "sources": [ ... search results ... ],
                        "query": "search query"
                    },
                    "categorization": {
                        "product_issues": [],
                        "conduct_issues": [],
                        "tags": [],
                        "patterns": {}
                    }
                },
                "metadata": {
                    "analysis_timestamp": "ISO-8601 timestamp",
                    "data_confidence": null,
                    "pattern_confidence": null
                }
            }
        ]
    }

    Example:
        >>> handler = ResearchOutputHandler(output_dir="data")
        >>> handler.save_research_output(results_by_company, companies_data)
    """

    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_metadata(self) -> Dict:
        """Generate standard metadata for research outputs."""
        return {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "type": "exclusions",
        }

    def format_company_analysis(self, company: Dict, results: Dict) -> Dict:
        """Format a single company's analysis results."""
        return {
            "company_name": company.get("Company", ""),
            "symbol": company.get("Symbol", ""),
            "primary_category": company.get("Category", ""),
            "current_criteria": company.get("Criteria", ""),
            "analysis": {
                "historical": results["analysis"],
                "evidence": {"sources": results["results"], "query": results["query"]},
                "categorization": {
                    "product_issues": [],
                    "conduct_issues": [],
                    "tags": [],
                    "patterns": {},
                },
            },
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "data_confidence": None,
                "pattern_confidence": None,
            },
        }

    def save_research_output(
        self,
        results_by_company: Dict[str, Dict],
        companies_data: List[Dict],
        prefix: str = "exclusions",
    ) -> Path:
        """
        Save research results to a single JSON file.

        Args:
            results_by_company: Dictionary mapping company names to their analysis results
            companies_data: List of original company data dictionaries
            prefix: Prefix for the output filename

        Returns:
            Path to the saved JSON file
        """
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")

        combined_results = {
            "meta": self.generate_metadata(),
            "companies": [
                self.format_company_analysis(
                    company, results_by_company[company["Company"]]
                )
                for company in companies_data
                if company["Company"] in results_by_company
            ],
        }

        output_path = self.output_dir / f"{prefix}_{timestamp}.json"
        with open(output_path, "w") as f:
            json.dump(combined_results, f, indent=2)

        logger.info(f"Saved combined analysis results to {output_path}")
        return output_path
