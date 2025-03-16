from __future__ import annotations

import asyncio
import csv
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
import marimo as mo

# API Configuration
api_config = {
    "OpenAIAPI": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "rate_limit": 3500,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "metadata": {
            "description": "OpenAI's GPT models for text generation and analysis.",
            "use_cases": ["Text analysis", "Content generation", "Research"],
            "capabilities": ["Generate text", "Answer questions", "Analyze content"],
        },
    },
    "DeepSeekAPI": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "rate_limit": 1000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "metadata": {
            "description": "DeepSeek's AI models for specialized analysis.",
            "use_cases": ["Research", "Analysis", "Content generation"],
            "capabilities": ["Generate text", "Answer questions", "Analyze data"],
        },
    },
    "FarfalleAPI": {
        "endpoint": "https://api.farfalle.ai/v1/completions",
        "rate_limit": 2000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("FARFALLE_API_KEY"),
        "metadata": {
            "description": "Farfalle's specialized models for entity analysis and research.",
            "use_cases": ["Entity analysis", "Research synthesis", "Data extraction"],
            "capabilities": [
                "Entity recognition",
                "Relationship mapping",
                "Controversy detection",
            ],
        },
    },
    "SearchAPI": {
        "endpoint": "https://api.search.ai/v1/search",
        "rate_limit": 5000,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("SEARCH_API_KEY"),
        "metadata": {
            "description": "Advanced search API for comprehensive web and news analysis.",
            "use_cases": ["News search", "Web scraping", "Source verification"],
            "capabilities": [
                "Real-time search",
                "Historical data",
                "Source credibility scoring",
            ],
        },
    },
    "AnthropicAPI": {
        "endpoint": "https://api.anthropic.com/v1/complete",
        "rate_limit": 1500,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "metadata": {
            "description": "Anthropic's Claude models for nuanced analysis and research.",
            "use_cases": [
                "Complex analysis",
                "Research synthesis",
                "Ethical evaluation",
            ],
            "capabilities": [
                "Nuanced reasoning",
                "Source evaluation",
                "Ethical analysis",
            ],
        },
    },
    "MistralAPI": {
        "endpoint": "https://api.mistral.ai/v1/chat",
        "rate_limit": 2500,
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("MISTRAL_API_KEY"),
        "metadata": {
            "description": "Mistral's advanced language models for specialized tasks.",
            "use_cases": [
                "Technical analysis",
                "Pattern recognition",
                "Data synthesis",
            ],
            "capabilities": [
                "Technical evaluation",
                "Pattern detection",
                "Comprehensive analysis",
            ],
        },
    },
}


async def query_api(api_name: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Query an API from the api_config."""
    config = api_config.get(api_name)
    if not config:
        return {"error": f"API {api_name} not found in configuration."}

    if config["queries_made"] >= config["rate_limit"]:
        return {"error": f"Rate limit exceeded for {api_name}."}

    try:
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                config["endpoint"],
                json=params,
                headers=headers,
            ) as response,
        ):
            if response.status == 200:
                data = await response.json()
                config["queries_made"] += 1
                return data
            return {"error": f"API returned status {response.status}"}
    except Exception as e:
        return {"error": f"Error querying {api_name}: {e!s}"}


def reset_query_counts() -> None:
    """Reset query counts for all APIs."""
    for config in api_config.values():
        config["queries_made"] = 0
        config["last_reset"] = datetime.now()


# Configuration cell
mo.md("## Company Controversy Analysis")

# API Key Management UI
provider_select = mo.ui.dropdown(
    options=list(api_config.keys()),
    value="OpenAIAPI",
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
new_key_input = mo.ui.text(
    value=current_key.value,
    label="API Key",
    password=True,
)


def update_api_key() -> str:
    provider = provider_select.value
    api_config[provider]["api_key"] = new_key_input.value
    os.environ[f"{provider.upper()}_API_KEY"] = new_key_input.value
    current_key.set(new_key_input.value)
    return f"Updated {provider} API key"


update_button = mo.ui.button("Update API Key", on_click=update_api_key)


# Reset Query Counts
def reset_counts() -> str:
    reset_query_counts()
    update_api_info()
    return "Reset query counts for all APIs"


reset_button = mo.ui.button("Reset Query Counts", on_click=reset_counts)

# CSV Upload
csv_file = mo.file("Upload companies CSV")


# Data structures
@dataclass
class EntityAnalysis:
    """Represents the analysis results for an entity."""

    name: str
    has_controversy: bool | None
    controversy_summary: str
    confidence_score: float
    sources: list[str]  # List of source URLs
    sector: str | None = None


# Database setup
class CompanyTracker:
    """Tracks which companies have been analyzed and stores their results."""

    def __init__(self, db_path: str = "company_analysis.db") -> None:
        """Initialize the company tracker with a SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS company_analyses (
                    company_name TEXT PRIMARY KEY,
                    sector TEXT,
                    has_controversy BOOLEAN,
                    controversy_summary TEXT,
                    confidence_score REAL,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            )


# Analysis functions
async def analyze_companies(companies: list[tuple[str, str]], provider: str):
    """Analyze companies for controversies using multiple APIs."""
    if not api_config[provider]["api_key"]:
        return mo.md("⚠️ Please set an API key first")

    CompanyTracker()
    results = []

    progress = mo.md("Starting analysis...")

    for company, sector in companies:
        try:
            progress.update(f"Analyzing {company}...")

            # Search for company information
            if provider == "SearchAPI":
                search_params = {
                    "query": f"{company} controversy news",
                    "limit": 10,
                    "sort": "recent",
                }
                search_results = await query_api("SearchAPI", search_params)
                sources = (
                    [result["url"] for result in search_results.get("results", [])]
                    if "error" not in search_results
                    else []
                )
            else:
                sources = []

            # Create analysis prompts for different aspects
            prompts = {
                "controversy": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a company controversy analyzer.",
                        },
                        {
                            "role": "user",
                            "content": f"Analyze {company} ({sector}) for any controversies or negative news.",
                        },
                    ],
                },
                "risk": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a risk assessment specialist.",
                        },
                        {
                            "role": "user",
                            "content": f"Assess potential risks and red flags for {company} in the {sector} sector.",
                        },
                    ],
                },
            }

            # Query selected API
            controversy_response = await query_api(
                provider,
                {**prompts["controversy"], "temperature": 0.7, "max_tokens": 500},
            )
            risk_response = await query_api(
                provider,
                {**prompts["risk"], "temperature": 0.7, "max_tokens": 500},
            )

            # If Farfalle API is available, get specialized entity analysis
            farfalle_analysis = None
            if "FarfalleAPI" in api_config and api_config["FarfalleAPI"]["api_key"]:
                farfalle_params = {
                    "entity": company,
                    "sector": sector,
                    "analysis_type": "comprehensive",
                }
                farfalle_analysis = await query_api("FarfalleAPI", farfalle_params)

            # Combine all analyses
            has_controversy = False
            controversy_summary = ""
            confidence_score = 0.0

            if "error" not in controversy_response:
                controversy_content = controversy_response["choices"][0]["message"][
                    "content"
                ]
                has_controversy = "controversy" in controversy_content.lower()
                controversy_summary = controversy_content
                confidence_score = 0.8

            if "error" not in risk_response:
                risk_content = risk_response["choices"][0]["message"]["content"]
                controversy_summary += f"\n\nRisk Assessment:\n{risk_content}"

            if farfalle_analysis and "error" not in farfalle_analysis:
                controversy_summary += (
                    f"\n\nSpecialized Analysis:\n{farfalle_analysis['analysis']}"
                )
                confidence_score = farfalle_analysis.get("confidence", confidence_score)

            result = EntityAnalysis(
                name=company,
                sector=sector,
                has_controversy=has_controversy,
                controversy_summary=controversy_summary,
                confidence_score=confidence_score,
                sources=sources,
            )
            results.append(result)

        except Exception as e:
            progress.update(f"Error analyzing {company}: {e}")

    return results


# Interactive analysis cell
async def run_analysis() -> None:
    if csv_file and api_config[provider_select.value]["api_key"]:
        companies = []
        csv_content = csv_file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(csv_content)
        for row in reader:
            companies.append((row["Company"], row.get("Sector", "")))

        results = await analyze_companies(companies, provider_select.value)

        # Display results
        mo.md("## Analysis Results")
        for result in results:
            mo.md(
                f"""
### {result.name}
- Sector: {result.sector}
- Has Controversy: {result.has_controversy}
- Confidence: {result.confidence_score}
- Summary: {result.controversy_summary}
            """,
            )
    else:
        mo.md("Please provide an API key and upload a CSV file to begin analysis.")


# Run the analysis
asyncio.run(run_analysis())
