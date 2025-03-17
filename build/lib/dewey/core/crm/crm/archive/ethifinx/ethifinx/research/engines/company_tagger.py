import json
import os
from typing import List, Dict, Optional
import logging
from pathlib import Path
from datetime import datetime
import asyncio
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
    def __init__(
        self,
        batch_size: int = 10,
        max_companies: int = 150,
        output_dir: str = "research_results/keywords",
        checkpoint_interval: int = 5,
        db_path: str = "research_results/research.db",
    ):
        self.batch_size = batch_size
        self.max_companies = max_companies
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.db_path = db_path
        self.session = None

    async def init_session(self):
        """Initialize aiohttp session if not already initialized"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    def load_checkpoint(self) -> Dict:
        """Load processing checkpoint if it exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
        return {"processed_companies": [], "last_batch": 0}

    def save_checkpoint(self, processed: List[str], last_batch: int):
        """Save processing checkpoint."""
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

    def load_research_results(self) -> List[Dict]:
        """Load companies from research results JSON files."""
        try:
            processed_ids = set(self.load_checkpoint().get("processed_companies", []))
            companies = []

            # Try multiple possible locations for research results
            possible_dirs = [
                Path("research_results"),
                Path("jupyter/research/research_results"),
                Path(os.path.expanduser("~/notebooks/research_results")),
                Path(
                    os.path.expanduser("~/notebooks/jupyter/research/research_results")
                ),
                Path.cwd() / "research_results",
            ]

            research_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists():
                    research_dir = dir_path
                    logger.info(f"Found research results directory at {dir_path}")
                    break

            if not research_dir:
                logger.error(
                    "Could not find research_results directory in any expected location"
                )
                return []

            # Look for search analysis files
            json_files = list(research_dir.glob("search_analysis_*.json"))
            logger.info(f"Found {len(json_files)} search analysis files")

            for json_file in json_files:
                try:
                    logger.info(f"Loading file: {json_file}")
                    with open(json_file, "r") as f:
                        data = json.load(f)

                    # Extract companies from the new structure
                    if isinstance(data, dict) and "companies" in data:
                        for company in data["companies"]:
                            company_name = company.get("company_name")
                            if company_name and company_name not in processed_ids:
                                # Restructure the data to match what we need
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

            # Remove duplicates based on company name
            unique_companies = {}
            for company in companies:
                name = company.get("name")
                if name and name not in unique_companies:
                    unique_companies[name] = company

            companies = list(unique_companies.values())
            logger.info(f"Successfully loaded {len(companies)} unique companies")

            # Limit to max companies if specified
            return companies[: self.max_companies]

        except Exception as e:
            logger.error(f"Error loading research results: {e}")
            return []

    def generate_prompt(self, company_data: Dict) -> str:
        """Create a detailed prompt for keyword generation."""
        # Extract relevant fields for the prompt
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
        """Generate keywords using DeepSeek API directly."""
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
        """Process a batch of companies to generate keywords."""
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

                # Save individual result
                self.save_company_result(result)
                results.append(result)

                logger.info(f"Generated {len(keywords)} keywords for {company_id}")

            except Exception as e:
                logger.error(f"Error processing company {company_id}: {e}")

        return results

    def save_company_result(self, result: Dict):
        """Save individual company result."""
        try:
            safe_id = "".join(
                c if c.isalnum() else "_" for c in str(result["company_id"])
            )
            company_file = self.output_dir / f"company_{safe_id}.json"
            with open(company_file, "w") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving company result: {e}")

    async def process_all_companies(self):
        """Process all companies in batches with checkpointing."""
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

                # Update processed companies
                for result in batch_results:
                    processed_ids.add(result["company_id"])

                # Save checkpoint
                if (i // self.batch_size) % self.checkpoint_interval == 0:
                    self.save_checkpoint(list(processed_ids), i)

                # Add delay between batches
                await asyncio.sleep(2)

            # Save final results
            self.save_final_results(all_results)
            self.save_checkpoint(list(processed_ids), len(companies))

            logger.info(f"Completed processing {len(all_results)} companies")

        except Exception as e:
            logger.error(f"Error in process_all_companies: {e}", exc_info=True)
            raise
        finally:
            await self.close()

    def save_final_results(self, results: List[Dict]):
        """Save final combined results."""
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


async def main():
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
