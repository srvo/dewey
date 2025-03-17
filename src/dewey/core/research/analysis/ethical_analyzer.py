
# Refactored from: ethical_analyzer
# Date: 2025-03-16T16:19:09.237774
# Refactor Version: 1.0
```python
#!/usr/bin/env python3
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from ethifinx.db import get_connection

# Enhanced logging setup
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"ethical_analysis_{TIMESTAMP}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class EthicalAnalyzer:
    """Analyzer for ethical considerations and controversies."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize the ethical analyzer.

        Args:
            data_dir: Optional path to data directory. Defaults to 'data'.
        """
        self.data_dir: Path = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.setup_analysis_tables()

    def _configure_rclone(self) -> Path:
        """Configures rclone with Hetzner credentials.

        Returns:
            Path: The path to the rclone config file.
        """
        rclone_config = f"""
        [hetzner]
        type = s3
        provider = Other
        access_key_id = {os.getenv('HETZNER_S3_ACCESS_KEY')}
        secret_access_key = {os.getenv('HETZNER_S3_SECRET_KEY')}
        endpoint = {os.getenv('S3_DATA_BUCKET')}
        """

        config_path = Path.home() / ".config" / "rclone" / "rclone.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(rclone_config)
        return config_path

    def _sync_file_to_s3(self, local_path: str, s3_path: str) -> None:
        """Syncs a file to S3 using rclone.

        Args:
            local_path: The local path of the file to sync.
            s3_path: The S3 path to sync the file to.
        """
        try:
            logger.info(f"Syncing {local_path} to S3: {s3_path}")
            subprocess.run(
                ["rclone", "copy", local_path, f"hetzner:{s3_path}"], check=True
            )
            logger.info("S3 sync complete")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to sync to S3: {str(e)}")

    def sync_to_s3(self) -> None:
        """Sync the database to S3 using rclone."""
        date_str = datetime.now().strftime("%y%m%d")
        s3_path = f"flows/ethical_analysis/{date_str}.db"

        config_path = self._configure_rclone()

        try:
            logger.info(f"Syncing database to S3: {s3_path}")
            self._sync_file_to_s3("data/research.db", s3_path)
        except Exception as e:
            logger.error(f"Failed to sync to S3: {str(e)}")
        finally:
            config_path.unlink(missing_ok=True)

    def setup_analysis_tables(self) -> None:
        """Create tables for storing ethical analysis results."""
        with get_connection() as conn:
            cursor = conn.cursor()
            logger.info("Setting up/verifying database tables")

            # Main analysis table - one row per controversy/issue
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ethical_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    symbol TEXT,

                    -- Primary categorization
                    primary_category TEXT,  -- 'product-based' or 'conduct-based'
                    issue_type TEXT,        -- specific category (e.g., 'animal cruelty', 'corruption')

                    -- Detailed analysis
                    description TEXT,       -- full description of the issue
                    historical_pattern TEXT, -- pattern of behavior over time
                    stakeholder_impact TEXT, -- who was affected and how

                    -- Evidence
                    sources TEXT,           -- JSON array of sources
                    earliest_known_date DATE,
                    latest_known_date DATE,

                    -- Severity metrics
                    severity_score INTEGER,  -- 1-10
                    pattern_score INTEGER,   -- 1-10, how systematic/repeated
                    evidence_strength INTEGER, -- 1-10, how well documented

                    -- Tags and metadata
                    tags TEXT,              -- JSON array of relevant tags
                    related_issues TEXT,     -- JSON array of related controversy IDs
                    notes TEXT,

                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            logger.info("Created/verified ethical_analysis table")

            # Aggregated company metrics
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS company_ethical_profile (
                    company_name TEXT PRIMARY KEY,
                    symbol TEXT,

                    -- Overall metrics
                    total_issues INTEGER,
                    avg_severity FLOAT,
                    max_severity INTEGER,

                    -- Category breakdowns
                    product_issues TEXT,    -- JSON object of product-based issues
                    conduct_issues TEXT,    -- JSON object of conduct-based issues

                    -- Timeline
                    earliest_controversy DATE,
                    latest_controversy DATE,
                    controversy_frequency TEXT, -- JSON object with temporal analysis

                    -- Pattern analysis
                    primary_concerns TEXT,      -- JSON array of main ethical concerns
                    recurring_patterns TEXT,    -- JSON object of behavioral patterns
                    stakeholder_impacts TEXT,   -- JSON object of affected groups

                    -- Meta analysis
                    data_confidence_score INTEGER,  -- 1-10, how complete is our data
                    pattern_confidence_score INTEGER, -- 1-10, how clear are the patterns

                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            logger.info("Created/verified company_ethical_profile table")
            conn.commit()

    def generate_analysis_prompt(self, company_row: Dict[str, Any]) -> str:
        """Generate a structured prompt for comprehensive ethical analysis.

        Args:
            company_row: A dictionary containing company data.

        Returns:
            str: The generated analysis prompt.
        """
        analysis_prompt = f"""Analyze the ethical profile and history of {company_row['Company']} ({company_row['Symbol']}).
        Current primary exclusion: {company_row['Category']} - {company_row['Criteria']}

        Please provide a comprehensive ethical analysis with the following structure:

        1. HISTORICAL ANALYSIS (40%):
        - Detailed timeline of controversies and ethical issues
        - Patterns of behavior and recurring issues
        - Evolution of company practices over time
        - Relationships between different ethical concerns

        2. EVIDENCE AND DOCUMENTATION (30%):
        - Specific incidents with dates
        - Primary sources and documentation
        - Regulatory actions and legal cases
        - Third-party investigations and reports
        - Stakeholder testimonies and impacts

        3. CATEGORIZATION AND METADATA (30%):

        A. Primary Categories:
        - Product-based issues (e.g., weapons, animal products, fossil fuels)
        - Conduct-based issues (e.g., corruption, labor violations, environmental damage)

        B. Specific Tags:
        - Issue types (e.g., animal cruelty, corruption, labor violations)
        - Affected stakeholders (e.g., workers, communities, environment)
        - Geographic scope
        - Severity indicators

        C. Pattern Analysis:
        - Systematic vs isolated issues
        - Response patterns to controversies
        - Corporate culture indicators
        - Governance implications

        Please provide as much detail as available. Don't limit the response length - thoroughness is preferred."""

        logger.info(f"Generated analysis prompt for {company_row['Company']}")
        return analysis_prompt

    def save_analysis_json(
        self, company_data: Dict[str, Any], timestamp: datetime
    ) -> None:
        """Save analysis results as JSON.

        Args:
            company_data: The analysis results to save.
            timestamp: The timestamp of the analysis.
        """
        date_str = timestamp.strftime("%y%m%d_%H%M%S")
        json_dir = self.data_dir / "analysis_json"
        json_dir.mkdir(parents=True, exist_ok=True)

        # Save local JSON
        json_path = json_dir / f"ethical_analysis_{date_str}.json"
        with open(json_path, "w") as f:
            json.dump(company_data, f, indent=2)
        logger.info(f"Saved analysis JSON to {json_path}")

        # Sync to S3
        s3_path = f"flows/ethical_analysis/{date_str}.json"
        self._sync_file_to_s3(str(json_path), s3_path)

    def run_analysis(self) -> Dict[str, Any]:
        """Run the ethical analysis flow.

        Returns:
            Dict[str, Any]: The analysis results.
        """
        run_timestamp = datetime.now()
        analysis_results: Dict[str, Any] = {
            "meta": {
                "timestamp": run_timestamp.isoformat(),
                "version": "1.0",
                "type": "ethical_analysis",
            },
            "companies": [],
        }

        try:
            logger.info("Starting comprehensive ethical analysis flow")

            # Read exclude list
            logger.info("Reading exclude.csv")
            df = pd.read_csv(self.data_dir / "exclude.csv")
            logger.info(f"Found {len(df)} companies to analyze")

            # Process each company
            for idx, row in df.iterrows():
                try:
                    company_name = row["Company"]
                    symbol = row["Symbol"]
                    logger.info(
                        f"[{idx+1}/{len(df)}] Starting analysis of {company_name} ({symbol})"
                    )

                    # Generate and run analysis
                    analysis_prompt = self.generate_analysis_prompt(row)
                    logger.info(f"Running search and analysis for {company_name}")

                    # TODO: Implement actual search/analysis logic here
                    # For now, creating placeholder structured data
                    company_analysis: Dict[str, Any] = {
                        "name": company_name,
                        "symbol": symbol,
                        "analysis_prompt": analysis_prompt,
                        "timestamp": datetime.now().isoformat(),
                    }
                    analysis_results["companies"].append(company_analysis)

                except Exception as e:
                    logger.error(f"Error analyzing {company_name}: {str(e)}")
                    continue

            # Save results
            self.save_analysis_json(analysis_results, run_timestamp)
            self.sync_to_s3()

            return analysis_results

        except Exception as e:
            logger.error(f"Analysis flow failed: {str(e)}")
            raise


if __name__ == "__main__":
    try:
        logging.info("=== Starting Ethical Analysis Process ===")
        logging.info(f"Log file: {LOG_FILE}")
        analyzer = EthicalAnalyzer()
        analysis_results = analyzer.run_analysis()
    except Exception as e:
        logging.error("Process failed with error", exc_info=True)
```
