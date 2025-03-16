```python
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import duckdb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("company_tagger.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class CompanyKeywordGenerator:
    """
    Generates keywords for companies using the DeepSeek API.

    Attributes:
        batch_size (int): The number of companies to process in each batch.
        max_companies (int): The maximum number of companies to process.
        output_dir (str): The directory to save the output files.
        checkpoint_interval (int): The interval (in batches) at which to save checkpoints.
        db_path (str): The path to the DuckDB database.
    """

    def __init__(
        self,
        batch_size: int = 10,
        max_companies: int = 150,
        output_dir: str = "research_results/keywords",
        checkpoint_interval: int = 5,
        db_path: str = "research_results/research.db",
    ) -> None:
        """
        Initializes the CompanyKeywordGenerator.

        Args:
            batch_size (int): The number of companies to process in each batch.
            max_companies (int): The maximum number of companies to process.
            output_dir (str): The directory to save the output files.
            checkpoint_interval (int): The interval (in batches) at which to save checkpoints.
            db_path (str): The path to the DuckDB database.
        """
        self.batch_size = batch_size
        self.max_companies = max_companies
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.db_path = db_path
        self.session: Optional[aiohttp.ClientSession] = None

    async def init_session(self) -> None:
        """Initializes aiohttp session if not already initialized."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Closes the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    def load_checkpoint(self) -> Dict:
        """Loads processing checkpoint if it exists.

        Returns:
            Dict: A dictionary containing the checkpoint data, or a default dictionary if the checkpoint file does not exist or cannot be loaded.
        """
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
        return {"processed_companies": [], "last_batch": 0}

    def save_checkpoint(self, processed: List[str], last_batch: int) -> None:
        """Saves processing checkpoint.

        Args:
            processed (List[str]): A list of company IDs that have been processed.
            last_batch (int): The index of the last batch that was processed.
        """
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump(
                    {
                        "processed_companies": processed,
                        "last_batch": last_batch,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                )
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    def _find_research_directory(self) -> Optional[Path]:
        """Finds the research results directory.

        Returns:
            Optional[Path]: The path to the research results directory, or None if not found.
        """
        possible_dirs = [
            Path("research_results"),
            Path("jupyter/research/research_results"),
            Path(os.path.expanduser("~/notebooks/research_results")),
            Path(os.path.expanduser("~/notebooks/jupyter/research/research_results")),
            Path.cwd() / "research_results",
        ]

        for dir_path in possible_dirs:
            if dir_path.exists():
                logger.info(f"Found research results directory at {dir_path}")
                return dir_path

        logger.error(
            "Could not find research_results directory in any expected location"
        )
        return None

    def load_research_results(self) -> List[Dict]:
        """Loads companies from research results JSON files.

        Returns:
            List[Dict]: A list of dictionaries, where each dictionary represents a company and its research results.
        """
        try:
            processed_ids = set(self.load_checkpoint().get("processed_companies", []))
            companies = []

            research_dir = self._find_research_directory()
            if not research_dir:
                return []

            json_files = list(research_dir.glob("search_analysis_*.json"))
            logger.info(f"Found {len(json_files)} search analysis files")

            for json_file in json_files:
                try:
                    logger.info(f"Loading file: {json_file}")
                    with open(json_file, "r") as f:
                        data = json.load(f)

                    if isinstance(data, dict) and "companies" in data:
                        for company in data["companies"]:
                            company_name = company.get("company_name")
                            if company_name and company_name not in processed_ids:
                                processed_company = {
                                    "name": company_name,
                                    "symbol": company.get("symbol", ""),
                                    "summary": company.get("summary", ""),
                                    "analysis": company.get("analysis", {}),
                                    "sources": company.get("sources", []),
                                    "metadata": {
                                        "file_source": str(json_file),
                                        "timestamp": data.get("meta", {}).get(
                                            "timestamp", ""
                                        ),
                                    },
                                }
                                companies.append(processed_company)

                except Exception as e:
                    logger.error(f"Error loading file {json_file}: {e}")
                    continue

            unique_companies = {}
            for company in companies:
                name = company.get("name")
                if name and name not in unique_companies:
                    unique_companies[name] = company

            companies = list(unique_companies.values())
            logger.info(f"Successfully loaded {len(companies)} unique companies")

            return companies[: self.max_companies]

        except Exception as e:
            logger.error(f"Error loading research results: {e}")
            return []

    def generate_prompt(self, company_data: Dict) -> str:
        """Creates a detailed prompt for keyword generation.

        Args:
            company_data (Dict): A dictionary containing the company's data.

        Returns:
            str: A string representing the prompt for keyword generation.
        """
        name = company_data.get("name", "")
        summary = company_data.get("summary", "")
        analysis = company_data.get("analysis", {})

        prompt = f"""
        Generate up to 50 relevant keywords or key phrases for semantic clustering and cohort analysis.
        Focus on these aspects:
        - Industry and sector classification
        - Business model and revenue streams
        - Products/Services offered
        - Market position and competitive advantages
        - ESG factors and sustainability initiatives
        - Risk factors and challenges
        - Geographic presence and market focus
        - Company scale and operational metrics
        - Notable characteristics or unique features

        Company Name: {name}

        Summary:
        {summary}

        Analysis:
        {json.dumps(analysis, indent=2)}

        Return ONLY a JSON array of strings representing the keywords/phrases.
        Example format: ["keyword1", "keyword2", "phrase 1", "phrase 2"]
        """
        return prompt

    async def generate_keywords(self, prompt: str) -> List[str]:
        """Generates keywords using DeepSeek API directly.

        Args:
            prompt (str): The prompt to use for keyword generation.

        Returns:
            List[str]: A list of keywords generated by the API.
        """
        await self.init_session()

        try:
            logger.info("Making DeepSeek API call with temperature 0.3")
            async with self.session.post(
                "https://api.deepseek.com/v1/completions",
                json={
                    "prompt": prompt,
                    "temperature": 0.3,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
            ) as response:
                if response.status != 200:
                    error_body = await response.text()
                    logger.error(
                        f"DeepSeek API error: {response.status} - {error_body}"
                    )
                    raise Exception(f"API call failed: {response.status}")

                result = await response.json()
                response_text = result.get("choices", [{}])[0].get("text", "[]")
                keywords = json.loads(response_text)
                logger.info(
                    f"Successfully received API response with {len(keywords)} keywords"
                )
                return keywords

        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            raise

    async def process_company_batch(self, companies: List[Dict]) -> List[Dict]:
        """Processes a batch of companies to generate keywords.

        Args:
            companies (List[Dict]): A list of dictionaries, where each dictionary represents a company.

        Returns:
            List[Dict]: A list of dictionaries, where each dictionary represents a company and its generated keywords.
        """
        results = []

        for company in companies:
            try:
                company_id = company.get("id") or company.get("name", "Unknown")
                logger.info(f"Processing company: {company_id}")

                prompt = self.generate_prompt(company)
                keywords = await self.generate_keywords(prompt)

                result = {
                    "company_id": company_id,
                    "company_name": company.get("name", "Unknown"),
                    "keywords": keywords,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "num_keywords": len(keywords),
                        "source_data_hash": hash(json.dumps(company, sort_keys=True)),
                    },
                }

                self.save_company_result(result)
                results.append(result)

                logger.info(f"Generated {len(keywords)} keywords for {company_id}")

            except Exception as e:
                logger.error(f"Error processing company {company_id}: {e}")

        return results

    def save_company_result(self, result: Dict) -> None:
        """Saves individual company result.

        Args:
            result (Dict): A dictionary containing the company's ID, name, and generated keywords.
        """
        try:
            safe_id = "".join(
                c if c.isalnum() else "_" for c in str(result["company_id"])
            )
            company_file = self.output_dir / f"company_{safe_id}.json"
            with open(company_file, "w") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving company result: {e}")

    async def process_all_companies(self) -> None:
        """Processes all companies in batches with checkpointing."""
        try:
            companies = self.load_research_results()
            if not companies:
                logger.error("No companies found to process!")
                return

            checkpoint = self.load_checkpoint()
            start_batch = checkpoint["last_batch"]

            logger.info(f"Starting processing from batch {start_batch}")
            logger.info(f"Total companies to process: {len(companies)}")

            all_results = []
            processed_ids = set(checkpoint["processed_companies"])

            for i in range(start_batch, len(companies), self.batch_size):
                batch = companies[i : i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1}")

                batch_results = await self.process_company_batch(batch)
                all_results.extend(batch_results)

                for result in batch_results:
                    processed_ids.add(result["company_id"])

                if (i // self.batch_size) % self.checkpoint_interval == 0:
                    self.save_checkpoint(list(processed_ids), i)

                await asyncio.sleep(2)

            self.save_final_results(all_results)
            self.save_checkpoint(list(processed_ids), len(companies))

            logger.info(f"Completed processing {len(all_results)} companies")

        except Exception as e:
            logger.error(f"Error in process_all_companies: {e}", exc_info=True)
            raise
        finally:
            await self.close()

    def save_final_results(self, results: List[Dict]) -> None:
        """Saves final combined results.

        Args:
            results (List[Dict]): A list of dictionaries, where each dictionary represents a company and its generated keywords.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"company_keywords_{timestamp}.json"

            with open(output_file, "w") as f:
                json.dump(
                    {
                        "timestamp": timestamp,
                        "total_companies": len(results),
                        "companies": results,
                        "metadata": {
                            "batch_size": self.batch_size,
                            "max_companies": self.max_companies,
                        },
                    },
                    f,
                    indent=2,
                )
            logger.info(f"Saved final results to {output_file}")
        except Exception as e:
            logger.error(f"Error saving final results: {e}")


async def main() -> None:
    """Main entry point with proper error handling."""
    try:
        generator = CompanyKeywordGenerator(
            batch_size=10,
            max_companies=150,
            checkpoint_interval=5,
            db_path="research_results/research.db",
        )

        await generator.process_all_companies()

    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
```
