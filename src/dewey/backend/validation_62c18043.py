import os

from backend.constants import ChatModel
from backend.utils import is_local_model, strtobool


def validate_model(model: ChatModel) -> bool:
    # Check if OpenRouter API key is set for all non-local models
    if not is_local_model(model):
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            msg = "OpenRouter API key (OPENAI_API_KEY) environment variable not found"
            raise ValueError(
                msg,
            )

        # Additional validation for GPT-4
        if model == ChatModel.GPT_4o:
            GPT4_ENABLED = strtobool(os.getenv("GPT4_ENABLED", True))
            if not GPT4_ENABLED:
                msg = "GPT4-o has been disabled. Please try a different model or self-host the app by following the instructions here: https://github.com/rashadphz/farfalle"
                raise ValueError(
                    msg,
                )
    else:
        # Validate local models
        LOCAL_MODELS_ENABLED = strtobool(os.getenv("ENABLE_LOCAL_MODELS", True))
        if not LOCAL_MODELS_ENABLED:
            msg = "Local models are not enabled"
            raise ValueError(msg)

    return True
