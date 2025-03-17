import os
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comprehensive API Configuration with Metadata
api_config = {
    "NewsAPI": {
        "endpoint": "https://newsapi.org/v2/everything",
        "rate_limit": 100,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("NEWS_API_KEY"),
        "metadata": {
            "description": "Provides access to news articles from various sources.",
            "use_cases": ["News aggregation", "Trend analysis", "Media monitoring"],
            "capabilities": ["Search articles by keyword", "Filter by date/source"],
        },
    },
    "ControversyAPI": {
        "endpoint": "http://localhost:8000/chat",
        "rate_limit": 50,  # Requests per hour
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("CONTROVERSY_API_KEY"),
        "metadata": {
            "description": "Identifies and analyzes controversies involving companies.",
            "use_cases": ["Risk assessment", "Reputation management"],
            "capabilities": ["Summarize controversies", "Identify involved entities"],
        },
    },
    "TwitterAPI": {
        "endpoint": "https://api.twitter.com/2/tweets/search/recent",
        "rate_limit": 450,  # Requests per 15 minutes
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("TWITTER_API_KEY"),
        "metadata": {
            "description": "Provides access to recent tweets and social media data.",
            "use_cases": ["Social media monitoring", "Sentiment analysis"],
            "capabilities": ["Search tweets by keyword", "Filter by date/user"],
        },
    },
    "GoogleNewsAPI": {
        "endpoint": "https://news.google.com/rss/search",
        "rate_limit": 1000,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("GOOGLE_NEWS_API_KEY"),
        "metadata": {
            "description": "Provides access to news articles from Google News.",
            "use_cases": ["News aggregation", "Trend analysis"],
            "capabilities": ["Search articles by keyword", "Filter by date/source"],
        },
    },
    "OpenAIAPI": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "rate_limit": 3500,  # Requests per minute
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "metadata": {
            "description": "Provides access to OpenAI's GPT models for text generation.",
            "use_cases": ["Text summarization", "Content generation", "Chatbots"],
            "capabilities": ["Generate text", "Answer questions", "Translate text"],
        },
    },
    "TavilyAPI": {
        "endpoint": "https://api.tavily.com/search",
        "rate_limit": 100,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("TAVILY_API_KEY"),
        "metadata": {
            "description": "Provides access to a search engine for web content.",
            "use_cases": ["Web search", "Data extraction"],
            "capabilities": ["Search web pages", "Extract structured data"],
        },
    },
    "BingAPI": {
        "endpoint": "https://api.bing.microsoft.com/v7.0/search",
        "rate_limit": 1000,  # Requests per month
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("BING_API_KEY"),
        "metadata": {
            "description": "Provides access to Bing's search engine.",
            "use_cases": ["Web search", "Data extraction"],
            "capabilities": ["Search web pages", "Filter by date/region"],
        },
    },
    "OpenFIGIAPI": {
        "endpoint": "https://api.openfigi.com/v3/mapping",
        "rate_limit": 500,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("OPENFIGI_API_KEY"),
        "metadata": {
            "description": "Provides mapping of financial instruments to identifiers.",
            "use_cases": ["Financial data analysis", "Instrument identification"],
            "capabilities": ["Map ISINs to FIGIs", "Retrieve instrument metadata"],
        },
    },
    "BraveSearchAPI": {
        "endpoint": "https://api.search.brave.com/v1/search",
        "rate_limit": 1000,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("BRAVE_SEARCH_API_KEY"),
        "metadata": {
            "description": "Provides access to Brave's privacy-focused search engine.",
            "use_cases": ["Web search", "Data extraction"],
            "capabilities": ["Search web pages", "Filter by date/region"],
        },
    },
    "ExaAIApi": {
        "endpoint": "https://api.exa.ai/v1/search",
        "rate_limit": 1000,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("EXA_AI_API_KEY"),
        "metadata": {
            "description": "Provides access to Exa's AI-powered search engine.",
            "use_cases": ["Web search", "Data extraction"],
            "capabilities": ["Search web pages", "Extract structured data"],
        },
    },
    "ApiTubeAPI": {
        "endpoint": "https://api.apitube.io/v1/search",
        "rate_limit": 1000,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("APITUBE_API_KEY"),
        "metadata": {
            "description": "Provides access to Apitube's search engine for web content.",
            "use_cases": ["Web search", "Data extraction"],
            "capabilities": ["Search web pages", "Extract structured data"],
        },
    },
    "AlphaVantageAPI": {
        "endpoint": "https://www.alphavantage.co/query",
        "rate_limit": 500,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("ALPHA_VANTAGE_API_KEY"),
        "metadata": {
            "description": "Provides access to financial and stock market data.",
            "use_cases": ["Stock analysis", "Market trends"],
            "capabilities": ["Retrieve stock prices", "Analyze market data"],
        },
    },
    "FinancialModelingPrepAPI": {
        "endpoint": "https://financialmodelingprep.com/api/v3",
        "rate_limit": 250,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("FINANCIAL_MODELING_PREP_API_KEY"),
        "metadata": {
            "description": "Provides access to financial data and company metrics.",
            "use_cases": ["Financial analysis", "Company valuation"],
            "capabilities": ["Retrieve financial statements", "Analyze company metrics"],
        },
    },
    "PolygonAPI": {
        "endpoint": "https://api.polygon.io/v2",
        "rate_limit": 5000,  # Requests per minute
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("POLYGON_API_KEY"),
        "metadata": {
            "description": "Provides access to real-time and historical market data.",
            "use_cases": ["Market analysis", "Trading strategies"],
            "capabilities": ["Retrieve stock prices", "Analyze market trends"],
        },
    },
    "DeepSeekAPI": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "rate_limit": 1000,  # Requests per day
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "metadata": {
            "description": "Provides access to DeepSeek's AI models for text generation.",
            "use_cases": ["Text summarization", "Content generation"],
            "capabilities": ["Generate text", "Answer questions"],
        },
    },
    "GitHubAPI": {
        "endpoint": "https://api.github.com",
        "rate_limit": 5000,  # Requests per hour
        "queries_made": 0,
        "last_reset": datetime.now(),
        "api_key": os.getenv("GITHUB_CLIENT_ID"),
        "metadata": {
            "description": "Provides access to GitHub's repositories and user data.",
            "use_cases": ["Code analysis", "Repository management"],
            "capabilities": ["Retrieve repository data", "Analyze code metrics"],
        },
    },
}

def add_new_api(name: str, endpoint: str, rate_limit: int, api_key: str, description: str, use_cases: list, capabilities: list):
    """
    Add a new API to the configuration with comprehensive validation.
    
    Args:
        name: Unique name for the API
        endpoint: Valid URL endpoint for the API
        rate_limit: Positive integer for rate limit
        api_key: API key string
        description: Description of the API
        use_cases: List of use cases
        capabilities: List of capabilities
        
    Raises:
        ValueError: If any validation fails
    """
    # Validate inputs
    if not name or not isinstance(name, str):
        raise ValueError("API name must be a non-empty string")
    
    if name in api_config:
        raise ValueError(f"API '{name}' already exists")
    
    if not endpoint or not isinstance(endpoint, str):
        raise ValueError("Endpoint must be a non-empty string")
    
    if not endpoint.startswith(('http://', 'https://')):
        raise ValueError("Endpoint must be a valid URL starting with http:// or https://")
    
    if not isinstance(rate_limit, int) or rate_limit <= 0:
        raise ValueError("Rate limit must be a positive integer")
    
    if not api_key or not isinstance(api_key, str):
        raise ValueError("API key must be a non-empty string")
    
    if not description or not isinstance(description, str):
        raise ValueError("Description must be a non-empty string")
    
    if not isinstance(use_cases, list) or not all(isinstance(uc, str) for uc in use_cases):
        raise ValueError("Use cases must be a list of strings")
    
    if not isinstance(capabilities, list) or not all(isinstance(cap, str) for cap in capabilities):
        raise ValueError("Capabilities must be a list of strings")
    
    try:
        api_config[name] = {
            "endpoint": endpoint,
            "rate_limit": rate_limit,
            "queries_made": 0,
            "last_reset": datetime.now(),
            "api_key": api_key,
            "metadata": {
                "description": description,
                "use_cases": use_cases,
                "capabilities": capabilities,
            },
        }
        logger.info(f"Successfully added new API: {name}")
    except Exception as e:
        logger.error(f"Failed to add API {name}: {str(e)}")
        raise RuntimeError(f"Failed to add API {name}: {str(e)}")

async def query_api(api_name: str, params: Dict[str, Any], db_manager=None) -> Optional[Dict[str, Any]]:
    """
    Query an API from the api_config.

    Args:
        api_name: Name of the API to query
        params: Dictionary of parameters for the API request
        db_manager: Optional DatabaseManager instance for logging

    Returns:
        JSON response from the API or None if request fails
    """
    config = api_config.get(api_name)
    if not config:
        return {"error": f"API {api_name} not found in configuration."}

    # Check rate limit
    if config["queries_made"] >= config["rate_limit"]:
        return {"error": f"Rate limit exceeded for {api_name}. Please wait until the next reset."}

    try:
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(config["endpoint"], params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    config["queries_made"] += 1
                
                    # Log the API call if db_manager is provided
                    if db_manager:
                        try:
                            db_manager.log_api_call(
                                api_name=api_name,
                                endpoint=config["endpoint"],
                                parameters=params,
                                response_status=response.status,
                                response_data=data
                            )
                        except Exception as e:
                            logger.error(f"Error logging API call: {str(e)}")
                
                    return data
                return {"error": f"API returned status {response.status}"}
    except Exception as e:
        return {"error": f"Error querying {api_name}: {str(e)}"}

def reset_query_counts():
    """
    Reset query counts for all APIs based on their rate limit periods.
    
    Raises:
        RuntimeError: If there's an error during the reset process
    """
    now = datetime.now()
    try:
        for api_name, config in api_config.items():
            try:
                # Validate config structure
                if not all(key in config for key in ["last_reset", "queries_made", "rate_limit"]):
                    logger.error(f"Invalid configuration for API {api_name}")
                    continue
                
                # Calculate time since last reset
                time_since_reset = now - config["last_reset"]
                
                # Determine reset period based on API name
                reset_period = {
                    "NewsAPI": timedelta(days=1),
                    "ControversyAPI": timedelta(hours=1),
                    "TwitterAPI": timedelta(minutes=15),
                    "GoogleNewsAPI": timedelta(days=1),
                    "OpenAIAPI": timedelta(minutes=1),
                    "TavilyAPI": timedelta(days=1),
                    "BingAPI": timedelta(days=30),
                    "OpenFIGIAPI": timedelta(days=1),
                    "BraveSearchAPI": timedelta(days=1),
                    "ExaAIApi": timedelta(days=1),
                    "ApiTubeAPI": timedelta(days=1),
                    "AlphaVantageAPI": timedelta(days=1),
                    "FinancialModelingPrepAPI": timedelta(days=1),
                    "PolygonAPI": timedelta(minutes=1),
                    "DeepSeekAPI": timedelta(days=1),
                    "GitHubAPI": timedelta(hours=1),
                }.get(api_name, timedelta(days=1))  # Default to daily reset
                
                if time_since_reset >= reset_period:
                    config["queries_made"] = 0
                    config["last_reset"] = now
                    logger.info(f"Reset query count for API {api_name}")
            except Exception as e:
                logger.error(f"Error resetting API {api_name}: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Critical error in reset_query_counts: {str(e)}")
        raise RuntimeError(f"Failed to reset query counts: {str(e)}")
