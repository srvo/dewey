"""Test script for the analysis tagger workflow."""

import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict, Optional
from ethifinx.research.engines.base import BaseEngine
from ethifinx.research.engines.deepseek import DeepSeekEngine, DateTimeEncoder
from ethifinx.research.workflows.analysis_tagger import (
    AnalysisTaggingWorkflow,
    AnalysisTags,
    AnalysisSummary
)
import duckdb

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Add file handler for detailed logging
log_file = Path(__file__).parent / 'analysis_tagger_test.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s'))
logger.addHandler(file_handler)

class DebugDeepSeekEngine(DeepSeekEngine, BaseEngine):
    """DeepSeek engine with debug logging."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        """Initialize with both parent classes."""
        BaseEngine.__init__(self)
        DeepSeekEngine.__init__(self, api_key, base_url)
    
    async def process(self) -> Dict[str, Any]:
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
            **kwargs
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
                logger.debug(f"Content repr: {repr(content)}")
                logger.debug(f"First 500 chars: {content[:500]}")
                logger.debug(f"Last 500 chars: {content[-500:] if len(content) > 500 else content}")
                logger.debug(f"JSON start index: {content.find('{')}")
                logger.debug(f"JSON end index: {content.rfind('}')}")
                
                # Try to find any JSON-like structure
                import re
                json_matches = re.findall(r'\{.*?\}', content, re.DOTALL)
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
                            logger.debug(f"Failed to parse as JSON: {str(e)}")
            
            logger.debug("=" * 80 + "\n")
            
            return response
        except Exception as e:
            logger.error("\n" + "=" * 80)
            logger.error("ERROR IN API CALL:")
            logger.error("=" * 80)
            logger.error(str(e))
            logger.error("=" * 80 + "\n")
            raise

class DebugAnalysisTaggingWorkflow(AnalysisTaggingWorkflow):
    """Analysis workflow with debug logging."""
    
    async def extract_tags(self, analysis_text: str, context: Optional[Dict[str, Any]] = None) -> AnalysisTags:
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
                    {"role": "user", "content": f"""Analyze this text and extract key metrics and tags. Return ONLY a valid JSON object matching the required schema.

Text to analyze:
{analysis_text}"""}
                ]
            )
            logger.debug("\nAPI Response:")
            logger.debug("-" * 40)
            logger.debug(json.dumps(response, indent=2))
            logger.debug("-" * 40)
            
            if response["error"]:
                raise ValueError(f"Tag extraction failed: {response['error']}")
            
            try:
                content = response["content"].strip()
                # Remove any leading/trailing text that might not be JSON
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start == -1 or json_end == 0:
                    raise ValueError(f"No JSON object found in response: {content}")
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse response as JSON: {str(e)}\nResponse: {content}")
        except Exception as e:
            logger.error("\nExtraction Error:")
            logger.error(str(e))
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
        logger.debug(f"Description: {company_data.meta.get('description', 'No description available')}")
        logger.debug(f"Context: {company_data.context}")
        if company_data.research_results:
            logger.debug("\nPrevious Research Results:")
            logger.debug(json.dumps(company_data.research_results, indent=2, cls=DateTimeEncoder))
        logger.debug("\nTick History:")
        for th in company_data.tick_history[:5]:
            logger.debug(f"  Date type: {type(th['date'])}")
            logger.debug(f"  Date value: {th['date']}")
            logger.debug(f"  Date repr: {repr(th['date'])}")
            logger.debug(f"  {th['date']}: {th['old_tick']} -> {th['new_tick']}")
        logger.debug("\nMeta last_tick_update:")
        last_update = company_data.meta.get('last_tick_update')
        if last_update:
            logger.debug(f"  Type: {type(last_update)}")
            logger.debug(f"  Value: {last_update}")
            logger.debug(f"  Repr: {repr(last_update)}")
        logger.debug("=" * 80)
        
        try:
            result = await super().process_analysis(company_data, context)
            logger.debug("\nProcessing Result:")
            logger.debug(json.dumps(result, indent=2, cls=DateTimeEncoder))
            return result
        except Exception as e:
            logger.error("\nProcessing Error:")
            logger.error(str(e))
            raise

# Load environment variables from .env file
env_path = Path(__file__).parents[1] / '.env'
load_dotenv(env_path)

# Get API key from environment
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY not found in .env file")

async def test_by_tick_range():
    """Test processing companies by tick range."""
    engine = DebugDeepSeekEngine(api_key=DEEPSEEK_API_KEY)
    workflow = DebugAnalysisTaggingWorkflow(engine)
    
    print("\nTesting companies with tick values 45-90:")
    print("----------------------------------------")
    
    try:
        async for result in workflow.process_companies_by_tick_range(min_tick=45, max_tick=90, limit=1):  # Just one for testing
            if "error" in result:
                logger.error(f"Error processing {result['ticker']}: {result['error']}")
                print(f"\n❌ Error processing {result['ticker']}: {result['error']}")
            else:
                logger.info(f"Successfully processed {result['ticker']}")
                print(f"\n✅ Processed {result['ticker']}:")
                print(f"Concern Level: {result['tags']['concern_level']}/5")
                print(f"Confidence: {result['tags']['confidence_score']:.2f}")
                print(f"Key Themes: {', '.join(result['tags']['primary_themes'][:3])}")
                print(f"Recommendation: {result['summary']['recommendation']}")
    except Exception as e:
        logger.exception("Error in test_by_tick_range")
        print(f"\n❌ Test error: {str(e)}")

async def test_specific_companies():
    """Test processing specific companies."""
    engine = DebugDeepSeekEngine(api_key=DEEPSEEK_API_KEY)
    workflow = DebugAnalysisTaggingWorkflow(engine)
    
    # Get top 30 companies by current tick value
    conn = duckdb.connect("data/research.duckdb")
    top_companies = conn.execute("""
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
    """).fetchall()
    conn.close()
    
    print("\nProcessing top 30 companies by tick value:")
    print("----------------------------------------")
    
    results = []
    try:
        for company in top_companies:
            print(f"\nAnalyzing {company[0]} ({company[1]}) - Tick: {company[2]}", end="", flush=True)
            async for result in workflow.process_companies_by_tickers([company[0]]):
                if "error" in result:
                    logger.error(f"Error processing {result['ticker']}: {result['error']}")
                    print(f" ❌ Error: {result['error']}")
                else:
                    logger.info(f"Successfully processed {result['ticker']}")
                    print(" ✅")
                    results.append({
                        'ticker': result['ticker'],
                        'name': company[1],
                        'tick': company[2],
                        'concern_level': result['tags']['concern_level'],
                        'confidence': result['tags']['confidence_score'],
                        'themes': result['tags']['primary_themes'][:3],
                        'recommendation': result['summary']['recommendation']
                    })
    except Exception as e:
        logger.exception("Error in test_specific_companies")
        print(f"\n❌ Test error: {str(e)}")
    
    # Print summary table
    if results:
        print("\nAnalysis Summary:")
        print("=" * 100)
        print(f"{'Ticker':<8} {'Name':<30} {'Tick':<5} {'Risk':<5} {'Conf':<5} {'Key Themes':<30}")
        print("-" * 100)
        for r in results:
            print(f"{r['ticker']:<8} {r['name'][:28]:<30} {r['tick']:<5} {r['concern_level']}/5   {r['confidence']:.2f}  {', '.join(r['themes'])[:30]}")
        print("=" * 100)
        
        print("\nDetailed Recommendations:")
        print("=" * 100)
        for r in results:
            print(f"\n{r['ticker']} ({r['name']}):")
            print(f"Recommendation: {r['recommendation']}")

async def test_simple_query():
    """Test a simple query to DeepSeek."""
    engine = DebugDeepSeekEngine(api_key=DEEPSEEK_API_KEY)
    
    print("\nTesting simple query:")
    print("-------------------")
    
    try:
        # Test with minimal prompt
        response = await engine.json_completion(
            messages=[{
                "role": "user",
                "content": "What is your favorite color?"
            }]
        )
        print("\n✅ Basic query response:")
        print(json.dumps(response, indent=2))
        
        # Test with explicit JSON format
        response = await engine.json_completion(
            messages=[{
                "role": "system",
                "content": """You are a helpful assistant that outputs valid JSON.
Example format:
{
    "color": "string",
    "reason": "string"
}"""
            },
            {
                "role": "user",
                "content": "What is your favorite color? Return a JSON object with 'color' and 'reason' fields."
            }]
        )
        print("\n✅ Formatted query response:")
        print(json.dumps(response, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

async def main():
    """Run all tests."""
    print("Starting Analysis Tagger Workflow Tests")
    print("======================================")
    logger.info("Starting tests")
    
    try:
        await test_specific_companies()
    except Exception as e:
        logger.exception("Error in main")
        print(f"\n❌ Fatal error: {str(e)}")
    finally:
        logger.info("Tests completed")

if __name__ == "__main__":
    asyncio.run(main()) 