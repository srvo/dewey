from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from backend.constants import ChatModel, get_model_string

if TYPE_CHECKING:
    from backend.api.db_manager import DatabaseManager


class OpenRouterManager:
    """Manages interactions with the OpenRouter API for model testing and information retrieval."""

    def __init__(self, db_manager: DatabaseManager, daily_limit: int = 1000) -> None:
        """Initializes the OpenRouterManager with a database manager and daily rate limit.

        Args:
            db_manager: The DatabaseManager instance for logging API calls and managing usage.
            daily_limit: The daily token limit for API usage.

        """
        self.db_manager = db_manager
        self.daily_limit = daily_limit
        self.test_image_url = (
            "https://raw.githubusercontent.com/OpenRouterTeam/openrouter/main/logo.png"
        )
        self.api_key = os.getenv("OPENAI_API_KEY", "your_openrouter_api_key_here")
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/OpenRouterTeam/openrouter",
            "Content-Type": "application/json",
        }

    async def format_vision_message(self, image_url: str) -> list[dict[str, Any]]:
        """Formats a message for vision models, including the image URL.

        Args:
            image_url: The URL of the image to be analyzed.

        Returns:
            A list containing a dictionary representing the formatted message.

        """
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ]

    async def _make_api_request(
        self,
        model_string: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Makes an API request to OpenRouter for chat completions.

        Args:
            model_string: The identifier of the model to use.
            messages: The list of messages to send to the model.

        Returns:
            A dictionary containing the success status and, if applicable, the error message.

        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": model_string,
                        "messages": messages,
                    },
                ) as response,
            ):
                response_data = await response.json()
                status_code = response.status

                await self.db_manager.log_api_call(
                    endpoint=model_string,
                    request_data=json.dumps({"messages": messages}),
                    response_data=json.dumps(response_data),
                    response_status=status_code,
                )

                if status_code == 200:
                    return {"success": True}
                return {
                    "success": False,
                    "error": response_data.get("error", {}).get(
                        "message",
                        "Unknown error",
                    ),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_model(
        self,
        model: ChatModel,
        test_type: str = "text",
        image_url: str | None = None,
    ) -> dict[str, Any]:
        """Tests a specified model with a given test type and optional image URL.

        Args:
            model: The ChatModel enum representing the model to test.
            test_type: The type of test to perform ("text", "vision", or "code").
            image_url: Optional image URL for vision tests.

        Returns:
            A dictionary containing the success status and, if applicable, the error message.

        """
        model_string = get_model_string(model)
        try:
            rate_limit_status = await self.get_rate_limit_status(model_string)
            if rate_limit_status["remaining"] <= 0:
                return {
                    "success": False,
                    "error": f"Rate limit exceeded for {model}. Please try again later.",
                }

            if test_type == "vision" and image_url:
                messages = await self.format_vision_message(image_url)
            elif test_type == "code":
                messages = [
                    {
                        "role": "user",
                        "content": "Write a simple Python function to calculate the factorial of a number.",
                    },
                ]
            else:
                messages = [
                    {
                        "role": "user",
                        "content": "Say hello and introduce yourself briefly.",
                    },
                ]

            return await self._make_api_request(model_string, messages)

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Retrieves a list of available models and their associated costs from the OpenRouter API.

        Returns:
            A list of dictionaries, where each dictionary contains information about a model.
            Returns an empty list if there is an error.

        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                ) as response,
            ):
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                return []
        except Exception:
            return []

    async def get_token_balance(self) -> dict[str, Any]:
        """Retrieves the current token balance from the OpenRouter API.

        Returns:
            A dictionary containing the available, capacity, and used token values.
            Returns default values if there is an error.

        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self.base_url}/auth/balance",
                    headers=self.headers,
                ) as response,
            ):
                if response.status == 200:
                    data = await response.json()
                    return {
                        "available": data.get("data", {}).get("credits", 0),
                        "capacity": self.daily_limit,
                        "used": self.daily_limit
                        - data.get("data", {}).get("credits", 0),
                    }
                return {
                    "available": 0,
                    "capacity": self.daily_limit,
                    "used": self.daily_limit,
                }
        except Exception:
            return {
                "available": 0,
                "capacity": self.daily_limit,
                "used": self.daily_limit,
            }

    async def get_rate_limit_status(
        self,
        model_string: str | None = None,
    ) -> dict[str, Any]:
        """Retrieves the current rate limit status, either for a specific model or for all models.

        Args:
            model_string: Optional model identifier to get the rate limit status for a specific model.
                         If None, returns the rate limit status for all models.

        Returns:
            A dictionary containing the used, limit, and remaining token values.
            If model_string is provided, returns a dictionary for that model.
            If model_string is None, returns a dictionary of dictionaries, one for each model.

        """
        try:
            usage = await self.db_manager.get_api_usage(
                endpoint=model_string if model_string else None,
                since=datetime.now() - timedelta(days=1),
            )

            if model_string:
                model_usage = usage.get(model_string, 0)
                return {
                    "used": model_usage,
                    "limit": self.daily_limit,
                    "remaining": max(0, self.daily_limit - model_usage),
                }
            return {
                model: {
                    "used": count,
                    "limit": self.daily_limit,
                    "remaining": max(0, self.daily_limit - count),
                }
                for model, count in usage.items()
            }
        except Exception:
            return (
                {"used": 0, "limit": self.daily_limit, "remaining": self.daily_limit}
                if model_string
                else {}
            )

    async def get_test_history(self, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieves the recent test history from the database.

        Args:
            limit: The maximum number of recent calls to retrieve.

        Returns:
            A list of dictionaries, where each dictionary represents a recent API call.
            Returns an empty list if there is an error.

        """
        try:
            return await self.db_manager.get_recent_calls(limit=limit)
        except Exception:
            return []
