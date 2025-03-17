from typing import Dict, Any
import os
from pydantic import BaseSettings, ValidationError, Field

DATA_DIR = "data"

class AppSettings(BaseSettings):
    deepinfra_api_key: str = Field(..., env="DEEPINFRA_API_KEY")
    model: str = Field("meta-llama/Llama-3.3-70B-Instruct-Turbo", env="MODEL")
    deepinfra_embedding_model: str = Field(..., env="DEEPINFRA_EMBEDDING_MODEL")
    llm_temperature: float = Field(0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(4096, env="LLM_MAX_TOKENS")
    storage_dir: str = Field("storage", env="STORAGE_DIR")
    storage_cache_dir: str = Field(".cache", env="STORAGE_CACHE_DIR")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

def get_config() -> AppSettings:
    try:
        return AppSettings()
    except ValidationError as e:
        missing = [err["loc"][0] for err in e.errors() if err["type"] == "value_error.missing"]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please check your .env file or environment configuration."
            ) from e
        raise

def get_llm_config(settings: AppSettings) -> Dict[str, Any]:
    return {
        "model": settings.model,
        "api_key": settings.deepinfra_api_key,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "api_base": os.getenv("DEEPINFRA_API_BASE", "https://api.deepinfra.com/v1"),
    }

def get_embedding_config(settings: AppSettings) -> Dict[str, Any]:
    return {
        "model_name": settings.deepinfra_embedding_model,
        "api_key": settings.deepinfra_api_key,
        "api_base": os.getenv("DEEPINFRA_API_BASE", "https://api.deepinfra.com/v1"),
    }

def get_storage_config(settings: AppSettings) -> Dict[str, str]:
    return {
        "storage_dir": settings.storage_dir,
        "cache_dir": settings.storage_cache_dir,
    }
