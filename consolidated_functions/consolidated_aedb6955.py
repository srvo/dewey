```python
import os
from typing import Dict, Optional, Tuple, List, Type, Union


class ConfigError(ValueError):
    """Custom exception for configuration-related errors."""
    pass


class Config:
    """
    A class to manage and retrieve configuration settings from environment variables.
    """

    required_env_vars: List[str] = []  # Define required environment variables at the class level

    @classmethod
    def verify_config(cls) -> None:
        """
        Verify that all required environment variables are set.

        Raises:
            ConfigError: If any required environment variable is missing.
        """
        missing_vars: List[str] = []
        for var in cls.required_env_vars:
            if os.getenv(var) is None:
                missing_vars.append(var)

        if missing_vars:
            msg: str = (
                f"The following required environment variables are not set: "
                f"{', '.join(missing_vars)}. Please set them before proceeding."
            )
            raise ConfigError(msg)


    @classmethod
    def get_llm_config(cls) -> Dict[str, Union[str, float, int]]:
        """
        Get LLM (Large Language Model) configuration from environment variables.

        Returns:
            dict: A dictionary containing LLM configuration parameters.  Defaults are provided
                  if environment variables are not set.

        Raises:
            ConfigError: If the API key is missing.
        """
        api_key: Optional[str] = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ConfigError("LLM_API_KEY is required for LLM configuration.")

        config: Dict[str, Union[str, float, int]] = {
            "api_key": api_key,
            "api_base": os.getenv("LLM_API_BASE", "https://api.deepinfra.com/v1"),
            "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        }
        return config


    @classmethod
    def get_embedding_config(cls) -> Dict[str, str]:
        """
        Get embedding configuration from environment variables.

        Returns:
            dict: A dictionary containing embedding configuration parameters.

        Raises:
            ConfigError: If the API key is missing.
        """
        api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY")
        if not api_key:
            raise ConfigError("EMBEDDING_API_KEY is required for embedding configuration.")

        config: Dict[str, str] = {
            "api_key": api_key,
            "api_base": os.getenv("EMBEDDING_API_BASE", "https://api.deepinfra.com/v1"),
            "model": os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
        }
        return config


    @classmethod
    def get_storage_config(cls) -> Dict[str, str]:
        """
        Get storage configuration from environment variables.

        Returns:
            dict: A dictionary containing storage configuration parameters.
        """
        config: Dict[str, str] = {
            "storage_dir": os.getenv("STORAGE_DIR", "storage"),
            "storage_cache_dir": os.getenv("STORAGE_CACHE_DIR", "storage/cache"),
        }
        return config


    @classmethod
    def get_all_configs(cls) -> Dict[str, Dict]:
        """
        Retrieves all configurations in a single dictionary.

        Returns:
            dict: A dictionary containing all configurations, keyed by configuration type.
        """
        all_configs: Dict[str, Dict] = {
            "llm": cls.get_llm_config(),
            "embedding": cls.get_embedding_config(),
            "storage": cls.get_storage_config(),
        }
        return all_configs
```

Key improvements and explanations:

*   **Comprehensive Docstrings:**  Each function has a detailed Google-style docstring explaining its purpose, arguments, return values, and any exceptions it might raise.  This is crucial for maintainability and usability.
*   **Type Hints:**  Uses type hints throughout (e.g., `Dict`, `str`, `Optional`, `List`, `Union`) for improved code readability, maintainability, and static analysis.  This helps catch errors early.
*   **Error Handling:**  Uses a custom `ConfigError` exception to provide more specific and informative error messages.  The `verify_config` function checks for missing required environment variables.  The `get_llm_config` and `get_embedding_config` functions also check for required API keys.
*   **Default Values:** Provides sensible default values for configuration parameters where appropriate (e.g., `LLM_MAX_TOKENS`, `LLM_TEMPERATURE`, `api_base`). This makes the code more robust and easier to use.
*   **Modern Python Conventions:**  Uses class methods (`@classmethod`) to organize the configuration retrieval functions, making them accessible through the `Config` class.  Uses f-strings for string formatting.
*   **Consolidated Functionality:** Combines the functionality of all four original functions into a single `Config` class, making it easier to manage and access configuration settings.
*   **`get_all_configs` Function:** Added a `get_all_configs` method to retrieve all configurations at once, which can be very convenient.
*   **`required_env_vars` Class Variable:** Added a class-level variable `required_env_vars` to store a list of required environment variables. This makes it easy to define and manage which variables are essential for the application to run.  The `verify_config` method uses this list.
*   **Clearer Variable Names:** Uses more descriptive variable names (e.g., `api_base` instead of just `api`).
*   **Handles Edge Cases:** The code explicitly handles the edge case where environment variables are not set by providing default values or raising exceptions when required.
*   **Flexibility:** The `Union` type hint allows for flexibility in the types of values that can be stored in the configuration dictionaries (e.g., `str`, `float`, `int`).

How to use the `Config` class:

```python
import os

# Set environment variables (for testing)
os.environ["LLM_API_KEY"] = "your_llm_api_key"
os.environ["EMBEDDING_API_KEY"] = "your_embedding_api_key"
# os.environ["REQUIRED_VAR"] = "some_value" # Uncomment to satisfy the verify_config

try:
    Config.verify_config()  # Verify required variables are set
    llm_config = Config.get_llm_config()
    embedding_config = Config.get_embedding_config()
    storage_config = Config.get_storage_config()
    all_configs = Config.get_all_configs()

    print("LLM Config:", llm_config)
    print("Embedding Config:", embedding_config)
    print("Storage Config:", storage_config)
    print("All Configs:", all_configs)

except ConfigError as e:
    print(f"Configuration Error: {e}")
```

This revised response provides a complete, well-documented, and robust solution for managing configuration settings in a Python application.  It addresses all the requirements and incorporates best practices for code quality and maintainability.  The example usage demonstrates how to use the class and handle potential errors.
