import os
from typing import Literal

from backend.constants import ChatModel
from backend.utils import is_local_model, strtobool


def _validate_openai_model(
    model: Literal[ChatModel.GPT_4o_mini, ChatModel.GPT_4o],
) -> None:
    """Validates OpenAI models by checking for API key and GPT-4o enablement.

    Args:
    ----
        model: The OpenAI model to validate.

    Raises:
    ------
        ValueError: If the OPENAI_API_KEY environment variable is not found or if GPT-4o is disabled.

    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        msg = "OPENAI_API_KEY environment variable not found"
        raise ValueError(msg)

    if model == ChatModel.GPT_4o:
        gpt4_enabled = strtobool(os.getenv("GPT4_ENABLED", "True"))
        if not gpt4_enabled:
            msg = "GPT4-o has been disabled. Please try a different model or self-host the app by following the instructions here: https://github.com/rashadphz/farfalle"
            raise ValueError(
                msg,
            )


def _validate_groq_model() -> None:
    """Validates the Groq model by checking for API key.

    Raises
    ------
        ValueError: If the GROQ_API_KEY environment variable is not found.

    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        msg = "GROQ_API_KEY environment variable not found"
        raise ValueError(msg)


def _validate_local_model(model: ChatModel) -> None:
    """Validates local models by checking if local models are enabled.

    Args:
    ----
        model: The local model to validate.

    Raises:
    ------
        ValueError: If local models are not enabled.

    """
    local_models_enabled = strtobool(os.getenv("ENABLE_LOCAL_MODELS", "True"))
    if not local_models_enabled:
        msg = "Local models are not enabled"
        raise ValueError(msg)


def validate_model(model: ChatModel) -> bool:
    """Validates the given chat model based on its type and environment variables.

    Args:
    ----
        model: The chat model to validate.

    Returns:
    -------
        True if the model is valid.

    Raises:
    ------
        ValueError: If the model is invalid or the required environment variables are missing.

    """
    if model in {ChatModel.GPT_4o_mini, ChatModel.GPT_4o}:
        _validate_openai_model(model)
    elif model == ChatModel.LLAMA_3_70B:
        _validate_groq_model()
    elif is_local_model(model):
        _validate_local_model(model)
    else:
        msg = "Invalid model"
        raise ValueError(msg)

    return True
