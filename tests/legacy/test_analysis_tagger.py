
# Refactored from: test_analysis_tagger
# Date: 2025-03-16T16:19:10.874840
# Refactor Version: 1.0
# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Test script for the analysis tagger workflow."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import duckdb
from dotenv import load_dotenv
from ethifinx.research.engines.base import BaseEngine
from ethifinx.research.engines.deepseek import DateTimeEncoder, DeepSeekEngine
from ethifinx.research.workflows.analysis_tagger import (
    AnalysisTaggingWorkflow,
    AnalysisTags,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Add file handler for detailed logging
log_file = Path(__file__).parent / "analysis_tagger_test.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] %(message)s"),
)
logger.addHandler(file_handler)


class DebugDeepSeekEngine(DeepSeekEngine, BaseEngine):
    """DeepSeek engine with debug logging."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
    ) -> None:
        """Initialize with both parent classes."""
        BaseEngine.__init__(self)
        DeepSeekEngine.__init__(self, api_key, base_url)

    async def process(self) -> dict[str, Any]:
        """Implement abstract method."""
        return {"status": "debug_engine"}

    async def json_completion(self, messages, **kwargs):
        """Log messages before sending to API."""
        logger.debug("\n" + "=" * 80)
        logger.debug("SENDING TO DEEPSEEK API:")
        logger.debug("=" * 80)

        # Log the full request payload
        request_payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "response_format": {"type": "json_object"},
            **kwargs,
        }
        logger.debug("REQUEST PAYLOAD:")
        logger.debug(json.dumps(request_payload, indent=2))

        logger.debug("\nMESSAGES BREAKDOWN:")
        for i, msg in enumerate(messages, 1):
            logger.debug(f"\nMessage {i}:")
            logger.debug("-" * 40)
            logger.debug(f"Role: {msg['role']}")
            logger.debug(f"Content:\n{msg['content']}")
            logger.debug("-" * 40)

        try:
            response = await super().json_completion(messages, **kwargs)

            logger.debug("\n" + "=" * 80)
            logger.debug("RECEIVED FROM DEEPSEEK API:")
            logger.debug("=" * 80)
            logger.debug("Raw response:")
            logger.debug(json.dumps(response, indent=2))

            if response.get("content"):
                logger.debug("\nContent analysis:")
                content = response["content"].strip()
                logger.debug(f"Content length: {len(content)}")
                logger.debug(f"Content type: {type(content)}")
                logger.debug(f"Content repr: {content!r}")
                logger.debug(f"First 500 chars: {content[:500]}")
                logger.debug(
                    f"Last 500 chars: {content[-500:] if len(content) > 500 else content}",
                )
                logger.debug(f"JSON start index: {content.find('{')}")
                logger.debug(f"JSON end index: {content.rfind('}')}")

                # Try to find any JSON-like structure
                import re

                json_matches = re.findall(r"\{.*?\}", content, re.DOTALL)
                if json_matches:
                    logger.debug("\nFound potential JSON structures:")
                    for i, match in enumerate(json_matches, 1):
                        logger.debug(f"\nPotential JSON {i}:")
                        logger.debug(match)
                        try:
                            parsed = json.loads(match)
                            logger.debug("Successfully parsed as JSON!")
                            logger.debug(json.dumps(parsed, indent=2))
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse as JSON: {e!s}")

            logger.debug("=" * 80 + "\n")

            return response
        except Exception as e:
            logger.exception("\n" + "=" * 80)
            logger.exception("ERROR IN API CALL:")
            logger.exception("=" * 80)
            logger.exception(str(e))
            logger.exception("=" * 80 + "\n")
            raise


class DebugAnalysisTaggingWorkflow(AnalysisTaggingWorkflow):
    """Analysis workflow with debug logging."""

    async def extract_tags(
        self,
        analysis_text: str,
        context: dict[str, Any] | None = None,
    ) -> AnalysisTags:
        """Log the extraction process."""
        logger.debug("\n" + "=" * 80)
        logger.debug("EXTRACTING TAGS")
        logger.debug("=" * 80)
        logger.debug("\nInput Text:")
        logger.debug("-" * 40)
        logger.debug(analysis_text)
        logger.debug("-" * 40)
        if context:
            logger.debug("\nContext:")
            logger.debug(json.dumps(context, indent=2))
        logger.debug("=" * 80)

        try:
            response = await self.engine.json_completion(
                messages=[
                    *self.engine.get_template("tag_extractor"),
                    {
                        "role": "user",
                        "content": f"""Analyze this text and extract key metrics and tags. Return ONLY a valid JSON object matching the required schema.

Text to analyze:
{analysis_text}""",
                    },
                ],
            )
            logger.debug("\nAPI Response:")
            logger.debug("-" * 40)
            logger.debug(json.dumps(response, indent=2))
            logger.debug("-" * 40)

            if response["error"]:
                msg = f"Tag extraction failed: {response['error']}"
                raise ValueError(msg)

            try:
                content = response["content"].strip()
                # Remove any leading/trailing text that might not be JSON
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start == -1 or json_end == 0:
                    msg = f"No JSON object found in response: {content}"
                    raise ValueError(msg)
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                msg = f"Failed to parse response as JSON: {e!s}\nResponse: {content}"
                raise ValueError(
                    msg,
                )
        except Exception as e:
            logger.exception("\nExtraction Error:")
            logger.exception(str(e))
            raise

    async def process_analysis(self, company_data, context=None):
        """Log company data before processing."""
        logger.debug("\n" + "=" * 80)
        logger.debug("PROCESSING COMPANY:")
        logger.debug("=" * 80)
        logger.debug(f"Ticker: {company_data.ticker}")
        logger.debug(f"Name: {company_data.name}")
        logger.debug(f"Current Tick: {company_data.current_tick}")
        logger.debug(f"Sector: {company_data.meta.get('sector', 'Unknown')}")
        logger.debug(f"Industry: {company_data.meta.get('industry', 'Unknown')}")
        logger.debug(
            f"Description: {company_data.meta.get('description', 'No description available')}",
        )
        logger.debug(f"Context: {company_data.context}")
        if company_data.research_results:
            logger.debug("\nPrevious Research Results:")
            logger.debug(
                json.dumps(
                    company_data.research_results,
                    indent=2,
                    cls=DateTimeEncoder,
                ),
            )
        logger.debug("\nTick History:")
        for th in company_data.tick_history[:5]:
            logger.debug(f"  Date type: {type(th['date'])}")
            logger.debug(f"  Date value: {th['date']}")
            logger.debug(f"  Date repr: {th['date']!r}")
            logger.debug(f"  {th['date']}: {th['old_tick']} -> {th['new_tick']}")
        logger.debug("\nMeta last_tick_update:")
        last_update = company_data.meta.get("last_tick_update")
        if last_update:
            logger.debug(f"  Type: {type(last_update)}")
            logger.debug(f"  Value: {last_update}")
            logger.debug(f"  Repr: {last_update!r}")
        logger.debug("=" * 80)

        try:
            result = await super().process_analysis(company_data, context)
            logger.debug("\nProcessing Result:")
            logger.debug(json.dumps(result, indent=2, cls=DateTimeEncoder))
            return result
        except Exception as e:
            logger.exception("\nProcessing Error:")
            logger.exception(str(e))
            raise


# Load environment variables from .env file
env_path = Path(__file__).parents[1] / ".env"
load_dotenv(env_path)

# Get API key from environment
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    msg = "DEEPSEEK_API_KEY not found in .env file"
    raise ValueError(msg)


async def test_by_tick_range() -> None:
    """Test processing companies by tick range."""
    engine = DebugDeepSeekEngine(api_key=DEEPSEEK_API_KEY)
    workflow = DebugAnalysisTaggingWorkflow(engine)

    try:
        async for result in workflow.process_companies_by_tick_range(
            min_tick=45,
            max_tick=90,
            limit=1,
        ):  # Just one for testing
            if "error" in result:
                logger.error(f"Error processing {result['ticker']}: {result['error']}")
            else:
                logger.info(f"Successfully processed {result['ticker']}")
    except Exception:
        logger.exception("Error in test_by_tick_range")


async def test_specific_companies() -> None:
    """Test processing specific companies."""
    engine = DebugDeepSeekEngine(api_key=DEEPSEEK_API_KEY)
    workflow = DebugAnalysisTaggingWorkflow(engine)

    # Get top 30 companies by current tick value
    conn = duckdb.connect("data/research.duckdb")
    top_companies = conn.execute(
        """
        WITH latest_ticks AS (
            SELECT
                ticker,
                new_tick as current_tick,
                date as last_updated
            FROM tick_history th1
            WHERE date = (
                SELECT MAX(date)
                FROM tick_history th2
                WHERE th2.ticker = th1.ticker
            )
        )
        SELECT
            u.ticker,
            u.name,
            lt.current_tick
        FROM latest_ticks lt
        JOIN universe u ON lt.ticker = u.ticker
        ORDER BY lt.current_tick DESC
        LIMIT 30
    """,
    ).fetchall()
    conn.close()

    results = []
    try:
        for company in top_companies:
            async for result in workflow.process_companies_by_tickers([company[0]]):
                if "error" in result:
                    logger.error(
                        f"Error processing {result['ticker']}: {result['error']}",
                    )
                else:
                    logger.info(f"Successfully processed {result['ticker']}")
                    results.append(
                        {
                            "ticker": result["ticker"],
                            "name": company[1],
                            "tick": company[2],
                            "concern_level": result["tags"]["concern_level"],
                            "confidence": result["tags"]["confidence_score"],
                            "themes": result["tags"]["primary_themes"][:3],
                            "recommendation": result["summary"]["recommendation"],
                        },
                    )
    except Exception:
        logger.exception("Error in test_specific_companies")

    # Print summary table
    if results:
        for _r in results:
            pass

        for _r in results:
            pass


async def test_simple_query() -> None:
    """Test a simple query to DeepSeek."""
    engine = DebugDeepSeekEngine(api_key=DEEPSEEK_API_KEY)

    try:
        # Test with minimal prompt
        await engine.json_completion(
            messages=[{"role": "user", "content": "What is your favorite color?"}],
        )

        # Test with explicit JSON format
        await engine.json_completion(
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful assistant that outputs valid JSON.
Example format:
{
    "color": "string",
    "reason": "string"
}""",
                },
                {
                    "role": "user",
                    "content": "What is your favorite color? Return a JSON object with 'color' and 'reason' fields.",
                },
            ],
        )

    except Exception:
        pass


async def main() -> None:
    """Run all tests."""
    logger.info("Starting tests")

    try:
        await test_specific_companies()
    except Exception:
        logger.exception("Error in main")
    finally:
        logger.info("Tests completed")


if __name__ == "__main__":
    asyncio.run(main())
