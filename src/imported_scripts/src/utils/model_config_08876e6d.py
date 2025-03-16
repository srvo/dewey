import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


class ChatModel(str, Enum):
    """Enumeration of available chat models."""

    LLAMA_3_70B = "llama-3-70b"
    GPT_4o = "gpt-4o"
    GPT_4o_mini = "gpt-4o-mini"
    COMMAND_R = "command-r"

    # Local models
    LOCAL_LLAMA_3 = "llama3.1"
    LOCAL_GEMMA = "gemma"
    LOCAL_MISTRAL = "mistral"
    LOCAL_PHI3_14B = "phi3:14b"

    # Custom models
    CUSTOM = "custom"


MODEL_MAPPINGS: dict[ChatModel, str] = {
    ChatModel.GPT_4o: "openai/gpt-4o",
    ChatModel.GPT_4o_mini: "openai/gpt-4o-mini",
    ChatModel.LLAMA_3_70B: "groq/llama-3.1-70b-versatile",
    ChatModel.LOCAL_LLAMA_3: "ollama_chat/llama3.1",
    ChatModel.LOCAL_GEMMA: "ollama_chat/gemma",
    ChatModel.LOCAL_MISTRAL: "ollama_chat/mistral",
    ChatModel.LOCAL_PHI3_14B: "ollama_chat/phi3:14b",
}


def _get_custom_model() -> str:
    """Retrieves the custom model string from environment variables.

    Raises:
        ValueError: If the CUSTOM_MODEL environment variable is not set.

    Returns:
        str: The custom model string.

    """
    custom_model = os.environ.get("CUSTOM_MODEL")
    if custom_model is None:
        msg = "CUSTOM_MODEL is not set"
        raise ValueError(msg)
    return custom_model


def _get_openai_model_string(model: ChatModel) -> str:
    """Retrieves the OpenAI model string, considering Azure mode.

    Args:
        model: The chat model.

    Returns:
        str: The OpenAI model string.

    """
    openai_mode = os.environ.get("OPENAI_MODE", "openai")
    if openai_mode == "azure":
        # Currently deployments are named "gpt-35-turbo" and "gpt-4o"
        name = MODEL_MAPPINGS[model].replace(".", "")
        return f"azure/{name}"
    return MODEL_MAPPINGS[model]


def get_model_string(model: ChatModel) -> str:
    """Retrieves the model string based on the ChatModel enum.

    Args:
        model: The chat model.

    Returns:
        str: The model string.

    """
    if model == ChatModel.CUSTOM:
        return _get_custom_model()

    if model in {ChatModel.GPT_4o_mini, ChatModel.GPT_4o}:
        return _get_openai_model_string(model)

    return MODEL_MAPPINGS[model]
