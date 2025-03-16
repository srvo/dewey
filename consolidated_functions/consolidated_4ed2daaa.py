import os
from typing import Any, Type, TypeVar, Union

from instructor import Instructor
from litellm import completion, set_verbose

# Define a type variable for the response model
T = TypeVar("T")


def validate_environment(model: str) -> dict[str, str]:
    """Validates the environment variables required for the LLM.

    Args:
        model: The name of the LLM model.

    Returns:
        A dictionary containing the validated environment variables.

    Raises:
        ValueError: If required environment variables are missing.
    """
    validation: dict[str, str] = {"missing_key": []}
    if "ollama" in model:
        if not os.environ.get("ollama_api_base"):
            validation["missing_key"].append("ollama_api_base")
        os.environ.setdefault("ollama_api_base", "http://localhost:11434")
    elif "openai" in model:
        if not os.environ.get("openai_api_key"):
            validation["missing_key"].append("openai_api_key")
        os.environ.setdefault("openai_api_base", "https://api.openai.com/v1")
    elif "azure" in model:
        if not os.environ.get("azure_openai_api_key"):
            validation["missing_key"].append("azure_openai_api_key")
        if not os.environ.get("azure_openai_api_base"):
            validation["missing_key"].append("azure_openai_api_base")
        if not os.environ.get("azure_openai_api_version"):
            validation["missing_key"].append("azure_openai_api_version")
        if not os.environ.get("azure_openai_api_deployment_name"):
            validation["missing_key"].append("azure_openai_api_deployment_name")
    if validation["missing_key"]:
        msg = f"Missing environment variables for model {model}: {validation['missing_key']}"
        raise ValueError(msg)
    return os.environ


class LLMClient:
    """
    A class that encapsulates interaction with various LLM models using LiteLLM and Instructor.
    """

    def __init__(self, model: str):
        """
        Initializes LLMClient with a specified model.

        Args:
            model: The name of the LLM model.
        """
        self.model = model
        self.client = self._create_instructor_client(model)

    def _create_instructor_client(self, model: str) -> Instructor:
        """
        Creates an Instructor client based on the model type.

        Args:
            model: The name of the LLM model.

        Returns:
            The configured Instructor client.
        """
        validate_environment(model)  # Ensure environment is set up before client creation
        return Instructor(completion_fn=completion, llm=model)

    def complete(self, prompt: str) -> str:
        """
        Completes the given prompt using LiteLLM.

        Args:
            prompt: The input prompt.

        Returns:
            The completion response.
        """
        response = completion(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    def structured_complete(self, response_model: Type[T], prompt: str) -> T:
        """
        Completes the given prompt and structures the response into a specified model.
        Uses the Instructor client for structured completion.

        Args:
            response_model: The type of the response model.
            prompt: The input prompt.

        Returns:
            An instance of the response model with the completion result.
        """
        result: T = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
        )
        return result
```
