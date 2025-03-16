import os
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import instructor
from dotenv import load_dotenv
from instructor.client import T
from litellm import completion
from litellm.utils import validate_environment
from llama_index.core.base.llms.types import CompletionResponse
from llama_index.llms.openai import OpenAI as LiteLLM

load_dotenv()


class BaseLLM(ABC):
    """Abstract base class for LLM implementations."""

    @abstractmethod
    async def astream(self, prompt: str) -> AsyncGenerator[CompletionResponse, None]:
        """Asynchronously streams the completion for a given prompt.

        Args:
        ----
            prompt: The input prompt.

        Returns:
        -------
            An asynchronous generator of completion responses.

        """

    @abstractmethod
    def complete(self, prompt: str) -> CompletionResponse:
        """Completes the given prompt.

        Args:
        ----
            prompt: The input prompt.

        Returns:
        -------
            The completion response.

        """

    @abstractmethod
    def structured_complete(self, response_model: type[T], prompt: str) -> T:
        """Completes the given prompt and structures the response into a specified model.

        Args:
        ----
            response_model: The type of the response model.
            prompt: The input prompt.

        Returns:
        -------
            An instance of the response model with the completion result.

        """


def _setup_environment(model: str) -> None:
    """Sets up the environment variables for the LLM.

    Args:
    ----
        model: The name of the LLM model.

    Raises:
    ------
        ValueError: If required environment variables are missing.

    """
    os.environ.setdefault("OLLAMA_API_BASE", "http://localhost:11434")
    os.environ.setdefault("OPENAI_API_BASE", "https://openrouter.ai/api/v1")

    validation = validate_environment(model)
    if validation["missing_keys"]:
        msg = f"Missing keys: {validation['missing_keys']}"
        raise ValueError(msg)


def _create_instructor_client(model: str):
    """Creates an Instructor client based on the model type.

    Args:
    ----
        model: The name of the LLM model.

    Returns:
    -------
        The configured Instructor client.

    """
    if "ollama_chat" in model:
        return instructor.from_litellm(completion, mode=instructor.Mode.MD_JSON)
    return instructor.from_litellm(completion)


class EveryLLM(BaseLLM):
    """Concrete class implementing BaseLLM using LiteLLM and Instructor."""

    def __init__(self, model: str) -> None:
        """Initializes EveryLLM with a specified model.

        Args:
        ----
            model: The name of the LLM model.

        """
        _setup_environment(model)

        self.llm = LiteLLM(model=model)
        self.client = _create_instructor_client(model)

    async def astream(self, prompt: str) -> AsyncGenerator[CompletionResponse, None]:
        """Asynchronously streams the completion for a given prompt using LiteLLM.

        Args:
        ----
            prompt: The input prompt.

        Returns:
        -------
            An asynchronous generator of completion responses.

        """
        return self.llm.astream_complete(prompt)

    def complete(self, prompt: str) -> CompletionResponse:
        """Completes the given prompt using LiteLLM.

        Args:
        ----
            prompt: The input prompt.

        Returns:
        -------
            The completion response.

        """
        return self.llm.complete(prompt)

    def structured_complete(self, response_model: type[T], prompt: str) -> T:
        """Completes the given prompt and structures the response into a specified model.
        Uses the Instructor client for structured completion.

        Args:
        ----
            response_model: The type of the response model.
            prompt: The input prompt.

        Returns:
        -------
            An instance of the response model with the completion result.

        """
        return self.client.chat.completions.create(
            model=self.llm.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
            headers={
                "HTTP-Referer": "https://research.sloane-collective.com",
                "X-Title": "Farfalle Research Assistant",
            },
        )
