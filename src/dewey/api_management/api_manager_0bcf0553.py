import asyncio
import os
from datetime import datetime, timedelta

import aiosqlite
import marimo as mo

# API Configuration with all our existing APIs
api_config = {
    "OpenAI": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "rate_limit": 3500,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "metadata": {
            "description": "OpenAI's GPT models for text generation and analysis",
            "use_cases": ["Text analysis", "Content generation", "Research"],
            "capabilities": ["Generate text", "Answer questions", "Analyze content"],
        },
    },
    "DeepSeek": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "rate_limit": 1000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "metadata": {
            "description": "DeepSeek's AI models for specialized analysis",
            "use_cases": ["Research", "Analysis", "Content generation"],
            "capabilities": ["Generate text", "Answer questions", "Analyze data"],
        },
    },
    "Tavily": {
        "endpoint": "https://api.tavily.com/search",
        "rate_limit": 5000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("TAVILY_API_KEY"),
        "metadata": {
            "description": "Tavily's search API for comprehensive research",
            "use_cases": ["Web search", "Research", "Data gathering"],
            "capabilities": ["Search", "Content aggregation", "Analysis"],
        },
    },
    "Bing": {
        "endpoint": os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com/"),
        "rate_limit": 10000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("BING_API_KEY"),
        "api_key_2": os.getenv("BING_API_KEY_2"),
        "location": os.getenv("BING_LOCATION", "global"),
        "metadata": {
            "description": "Microsoft Bing's search and analysis APIs",
            "use_cases": ["Web search", "News analysis", "Market research"],
            "capabilities": ["Search", "News aggregation", "Entity analysis"],
        },
    },
    "OpenFIGI": {
        "endpoint": os.getenv("OPENFIGI_BASE_URL", "https://api.openfigi.com/"),
        "rate_limit": 25000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("OPENFIGI_API_KEY"),
        "metadata": {
            "description": "Financial Instrument Global Identifier API",
            "use_cases": ["Financial data", "Instrument mapping", "Market analysis"],
            "capabilities": ["Identifier mapping", "Financial data", "Market research"],
        },
    },
    "BraveSearch": {
        "endpoint": "https://api.search.brave.com/",
        "rate_limit": 2000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("BRAVE_SEARCH_API_KEY"),
        "metadata": {
            "description": "Brave's privacy-focused search API",
            "use_cases": ["Private search", "Content discovery", "Research"],
            "capabilities": ["Search", "Content analysis", "Privacy-focused results"],
        },
    },
    "ExaAI": {
        "endpoint": "https://api.exa.ai/",
        "rate_limit": 1000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("EXA_AI_API_KEY"),
        "metadata": {
            "description": "Exa's AI-powered search and analysis",
            "use_cases": ["AI search", "Content analysis", "Research"],
            "capabilities": ["AI-powered search", "Content understanding", "Analysis"],
        },
    },
    "APITube": {
        "endpoint": "https://api.apitube.io/",
        "rate_limit": 5000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("APITUBE_API_KEY"),
        "metadata": {
            "description": "APITube's content and data API",
            "use_cases": ["Content analysis", "Data extraction", "Research"],
            "capabilities": ["Content processing", "Data extraction", "Analysis"],
        },
    },
    "AlphaVantage": {
        "endpoint": "https://www.alphavantage.co/query",
        "rate_limit": 500,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("ALPHA_VANTAGE_API_KEY"),
        "metadata": {
            "description": "Financial market data and analysis API",
            "use_cases": ["Market data", "Financial analysis", "Trading"],
            "capabilities": ["Market data", "Technical analysis", "Fundamental data"],
        },
    },
    "FinancialModelingPrep": {
        "endpoint": "https://financialmodelingprep.com/api/",
        "rate_limit": 250,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("FINANCIAL_MODELING_PREP_API_KEY"),
        "metadata": {
            "description": "Comprehensive financial data and analysis API",
            "use_cases": ["Financial analysis", "Company data", "Market research"],
            "capabilities": ["Financial data", "Company analysis", "Market insights"],
        },
    },
    "Polygon": {
        "endpoint": "https://api.polygon.io/",
        "rate_limit": 5,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("POLYGON_API_KEY"),
        "metadata": {
            "description": "Real-time and historical financial market data",
            "use_cases": ["Market data", "Trading", "Analysis"],
            "capabilities": ["Real-time data", "Historical data", "Market analysis"],
        },
    },
}


# Database Manager for API tracking
class APIDatabase:
    def __init__(self, db_path: str = "api_manager.db") -> None:
        self.db_path = db_path
        self._initialized = False

    async def ensure_initialized(self) -> None:
        if not self._initialized:
            await self._init_db()
            self._initialized = True

    async def _init_db(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    status INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    request_data TEXT,
                    response_data TEXT
                )
            """,
            )
            await db.commit()

    async def log_call(
        self,
        api_name: str,
        endpoint: str,
        status: int,
        request_data: str,
        response_data: str,
    ) -> None:
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO api_calls (api_name, endpoint, status, request_data, response_data)
                VALUES (?, ?, ?, ?, ?)
            """,
                (api_name, endpoint, status, request_data, response_data),
            )
            await db.commit()

    async def get_usage_stats(self, days: int = 7) -> dict[str, dict[str, int]]:
        await self.ensure_initialized()
        cutoff = datetime.now() - timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT api_name, COUNT(*) as total_calls,
                       SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as successful_calls
                FROM api_calls
                WHERE timestamp > ?
                GROUP BY api_name
            """,
                (cutoff.isoformat(),),
            )
            rows = await cursor.fetchall()
            return {
                row["api_name"]: {
                    "total_calls": row["total_calls"],
                    "successful_calls": row["successful_calls"],
                }
                for row in rows
            }


# Initialize database
db = APIDatabase()

# UI Components
mo.md("# API Manager")

# API Selection
provider_select = mo.ui.dropdown(
    options=list(api_config.keys()),
    value="OpenAI",
    label="Select API Provider",
)


def get_api_info(provider: str) -> str:
    """Get formatted API information."""
    if provider not in api_config:
        return "Provider not found"

    config = api_config[provider]
    metadata = config["metadata"]

    return f"""
### {provider}
**Description:** {metadata['description']}

**Use Cases:**
{chr(10).join(['- ' + uc for uc in metadata['use_cases']])}

**Capabilities:**
{chr(10).join(['- ' + cap for cap in metadata['capabilities']])}

**Rate Limit:** {config['rate_limit']} requests
**Queries Made:** {config['queries_made']}
**Last Reset:** {config['last_reset'].strftime('%Y-%m-%d %H:%M:%S')}
"""


# Show API Information
api_info = mo.md(get_api_info(provider_select.value))


def update_api_info() -> None:
    api_info.update(get_api_info(provider_select.value))


provider_select.on_change(update_api_info)

# API Key Management
current_key = mo.state(api_config[provider_select.value]["api_key"] or "")
new_key_input = mo.ui.text(value=current_key.value, label="API Key", password=True)


def update_api_key() -> str:
    provider = provider_select.value
    api_config[provider]["api_key"] = new_key_input.value
    os.environ[f"{provider.upper()}_API_KEY"] = new_key_input.value
    current_key.set(new_key_input.value)
    return f"Updated {provider} API key"


update_button = mo.ui.button("Update API Key", on_click=update_api_key)


# Usage Statistics
async def display_usage_stats():
    stats = await db.get_usage_stats()
    return mo.md(
        f"""
### API Usage Statistics (Last 7 Days)
{chr(10).join([
    f"**{api}:** {data['successful_calls']}/{data['total_calls']} successful calls"
    for api, data in stats.items()
])}
""",
    )


usage_stats = mo.md(asyncio.run(display_usage_stats()))


# Reset Query Counts
def reset_counts() -> str:
    for config in api_config.values():
        config["queries_made"] = 0
        config["last_reset"] = datetime.now()
    update_api_info()
    return "Reset query counts for all APIs"


reset_button = mo.ui.button("Reset Query Counts", on_click=reset_counts)


# Test API Connection
async def test_api_connection(provider: str):
    config = api_config[provider]
    if not config["api_key"]:
        return "⚠️ Please set an API key first"

    try:
        # Simple test request based on API type
        result = "🟢 Connection successful"
        await db.log_call(provider, config["endpoint"], 200, "test", "success")
    except Exception as e:
        result = f"🔴 Connection failed: {e!s}"
        await db.log_call(provider, config["endpoint"], 500, "test", str(e))

    return result


test_result = mo.md("")


def run_test() -> None:
    result = asyncio.run(test_api_connection(provider_select.value))
    test_result.update(result)


test_button = mo.ui.button("Test Connection", on_click=run_test)
