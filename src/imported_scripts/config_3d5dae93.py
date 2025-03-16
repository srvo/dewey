import os
from typing import Any

# Make DATA_DIR a module-level constant
DATA_DIR = "data"


class Config:
    REQUIRED_ENV_VARS = ["DEEPINFRA_API_KEY", "MODEL", "DEEPINFRA_EMBEDDING_MODEL"]

    @classmethod
    def verify_config(cls) -> None:
        """Verify all required environment variables are set."""
        missing_vars = [var for var in cls.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            raise ValueError(
                msg,
            )

    @classmethod
    def get_llm_config(cls) -> dict[str, Any]:
        """Get LLM configuration from environment variables."""
        return {
            "model": os.getenv("MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            "api_key": os.getenv("DEEPINFRA_API_KEY"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
            "api_base": os.getenv("DEEPINFRA_API_BASE", "https://api.deepinfra.com/v1"),
        }

    @classmethod
    def get_embedding_config(cls) -> dict[str, Any]:
        return {
            "model_name": os.getenv("DEEPINFRA_EMBEDDING_MODEL"),
            "api_key": os.getenv("DEEPINFRA_API_KEY"),
            "api_base": os.getenv("DEEPINFRA_API_BASE", "https://api.deepinfra.com/v1"),
        }

    @classmethod
    def get_storage_config(cls) -> dict[str, str]:
        return {
            "storage_dir": os.getenv("STORAGE_DIR", "storage"),
            "cache_dir": os.getenv("STORAGE_CACHE_DIR", ".cache"),
        }
