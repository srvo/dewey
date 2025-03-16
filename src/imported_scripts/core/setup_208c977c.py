import os
from pathlib import Path

from posting import Posting


def setup(posting: Posting) -> None:
    """Initialize all API tokens and environment variables."""
    # Only set tokens if they haven't been set in this session
    if not posting.get_variable("TOKENS_INITIALIZED"):
        # Load tokens from .env file
        env_path = Path.home() / "rawls" / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        posting.set_variable(key.strip(), value.strip().strip("\"'"))

        # Internal Services
        if not posting.get_variable("ANYTHING_LLM_TOKEN"):
            posting.set_variable(
                "ANYTHING_LLM_TOKEN",
                os.getenv("ANYTHING_LLM_TOKEN", ""),
            )

        if not posting.get_variable("LANGFLOW_API_KEY"):
            posting.set_variable("LANGFLOW_API_KEY", os.getenv("LANGFLOW_API_KEY", ""))

        # External Services
        if not posting.get_variable("TAVILY_API_KEY"):
            posting.set_variable("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY", ""))

        if not posting.get_variable("BING_API_KEY"):
            posting.set_variable("BING_API_KEY", os.getenv("BING_API_KEY", ""))
            posting.set_variable(
                "BING_ENDPOINT",
                os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com"),
            )

        if not posting.get_variable("DEEPSEEK_API_KEY"):
            posting.set_variable("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))

        if not posting.get_variable("OPENROUTER_API_KEY"):
            posting.set_variable(
                "OPENROUTER_API_KEY",
                os.getenv("OPENROUTER_API_KEY", ""),
            )
            posting.set_variable(
                "HTTP_REFERER",
                os.getenv("HTTP_REFERER", "http://localhost:3000"),
            )
            posting.set_variable("X_TITLE", os.getenv("X_TITLE", "Local Development"))

        # Mark tokens as initialized for this session
        posting.set_variable("TOKENS_INITIALIZED", "true")
        posting.notify("API tokens initialized", "Setup", "information")

    # Set request-specific variables
    posting.set_variable("SESSION_ID", f"session_{os.urandom(4).hex()}")

    # Log setup completion
