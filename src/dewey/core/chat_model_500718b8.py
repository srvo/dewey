from __future__ import annotations

import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


class ChatModel(Enum):
    # Local models
    LOCAL_LLAMA_3 = "llama3.1"
    LOCAL_GEMMA = "gemma"
    LOCAL_MISTRAL = "mistral"
    LOCAL_PHI3_14B = "phi3:14b"

    # Free OpenRouter models
    GEMINI_EXP = "gemini-exp"
    GEMINI_FLASH_THINKING = "gemini-flash-thinking"
    LLAMA_3_3B = "llama-3-3b"
    LLAMA_3_90B_VISION = "llama-3-90b-vision"
    GEMINI_FLASH = "gemini-flash"

    # DeepSeek models (efficient with caching)
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_CODE = "deepseek-code"
    DEEPSEEK_VISION = "deepseek-vision"

    # Custom models
    CUSTOM = "custom"

    def __str__(self) -> str:
        return self.value


model_mappings: dict[ChatModel, str] = {
    ChatModel.LOCAL_LLAMA_3: "ollama_chat/llama3.1",
    ChatModel.LOCAL_GEMMA: "ollama_chat/gemma",
    ChatModel.LOCAL_MISTRAL: "ollama_chat/mistral",
    ChatModel.LOCAL_PHI3_14B: "ollama_chat/phi3:14b",
    # Free OpenRouter models - using actual model IDs from OpenRouter
    ChatModel.GEMINI_EXP: "google/gemini-pro",
    ChatModel.GEMINI_FLASH_THINKING: "google/gemini-pro",
    ChatModel.LLAMA_3_3B: "meta-llama/llama-3.2-3b-instruct:free",
    ChatModel.LLAMA_3_90B_VISION: "meta-llama/llama-3.2-90b-vision-instruct:free",
    ChatModel.GEMINI_FLASH: "google/gemini-pro-vision",
    # DeepSeek models with efficient caching for repeated prompts
    ChatModel.DEEPSEEK_CHAT: "deepseek/deepseek-chat-v2.5",
    ChatModel.DEEPSEEK_CODE: "qwen/qwen-2.5-coder-32b-instruct",
    ChatModel.DEEPSEEK_VISION: "meta-llama/llama-3.2-90b-vision-instruct:free",
}


def get_model_string(model: ChatModel) -> str:
    if model == ChatModel.CUSTOM:
        custom_model = os.environ.get("CUSTOM_MODEL")
        if custom_model is None:
            msg = "CUSTOM_MODEL is not set"
            raise ValueError(msg)
        return custom_model

    return model_mappings[model]
