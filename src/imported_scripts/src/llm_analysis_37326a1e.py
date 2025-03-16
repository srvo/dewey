import asyncio
import json
import logging
import os
import random
import sys

import aiohttp

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432",
}


async def get_market_insights(
    symbol: str,
    name: str,
    session,
    attempt=1,
    max_attempts=3,
) -> str:
    """Get market insights for a stock using the Farfalle API with exponential backoff."""
    url = "http://localhost:8000/chat"

    # Enhanced query to focus on specific aspects
    query = (
        f"Analyze {symbol} ({name}). Focus on:\n"
        "1. Recent news stories and press releases\n"
        "2. Any controversies or regulatory issues\n"
        "3. Material changes in business operations\n"
        "4. Industry trends affecting the company\n"
        "5. Key risks and opportunities\n"
        "Provide a concise summary of findings."
    )

    payload = {"query": query, "model": "gpt-4o", "temperature": 0.7, "history": []}

    try:
        # Add jitter to delay to prevent thundering herd
        delay = (2**attempt + random.uniform(0, 1)) * 5
        await asyncio.sleep(delay)

        async with session.post(url, json=payload, timeout=60) as response:

            if response.status == 429:  # Too Many Requests
                if attempt < max_attempts:
                    logger.warning(
                        f"Rate limited for {symbol}, attempt {attempt}/{max_attempts}. Retrying after {delay} seconds...",
                    )
                    await asyncio.sleep(delay)  # Wait before retry
                    return await get_market_insights(
                        symbol,
                        name,
                        session,
                        attempt + 1,
                        max_attempts,
                    )
                return "Rate limit exceeded, please try again later"

            if response.status != 200:
                logger.error(f"Error getting insights for {symbol}: {response.status}")
                return f"Error: HTTP {response.status}"

            insights = ""
            try:
                async for line in response.content:
                    if line:
                        try:
                            event_data = line.decode("utf-8").strip()
                            if event_data.startswith("data: "):
                                event_json = json.loads(
                                    event_data[6:],
                                )  # Skip 'data: ' prefix
                                if event_json.get("event") == "text-chunk":
                                    chunk = event_json.get("data", {}).get("text", "")
                                    insights += chunk
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.exception(f"Error processing stream for {symbol}: {e!s}")
                return f"Error processing stream: {e!s}"

            return insights.strip() if insights else "No insights available"
    except TimeoutError:
        logger.exception(f"Timeout getting insights for {symbol}")
        return "Error: Request timeout"
    except Exception as e:
        logger.exception(f"Error analyzing {symbol}: {e!s}")
        return f"Error: {e!s}"


async def analyze_stocks() -> None:
    """Analyze stocks and update the database with insights."""
    try:
        # Test single stock analysis
        async with aiohttp.ClientSession() as session:
            await get_market_insights(
                "ECAT",
                "European Sustainable Growth Acquisition Corp.",
                session,
            )

    except Exception as e:
        logger.exception(f"Error: {e!s}")


if __name__ == "__main__":
    asyncio.run(analyze_stocks())
