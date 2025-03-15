"""OpenRouter API client with rate limiting."""
import time
import logging
from typing import Optional, Tuple

import httpx

class RateLimiter:
    """Global rate limiter singleton to track usage across instances"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.limits = {}  # Model: (RPM, TPM, last_reset_time)
            cls._instance.usage = {}   # Model: (tokens_used, requests_made)
        return cls._instance

    def _get_limits(self, model: str) -> Tuple[int, int, int]:
        """
        Fetch rate limits for a given model from OpenRouter's metadata endpoint.
        
        Args:
            model: The model name.
            
        Returns:
            A tuple containing RPM (requests per minute), TPM (tokens per minute), and the last reset time.
        """
        try:
            response = httpx.get(f"https://openrouter.ai/api/v1/models/{model}")
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            rpm = data.get("rpm", 60)  # Requests per minute (default to 60 if not specified)
            tpm = data.get("tpm", 400000)  # Tokens per minute (default to 400k if not specified)
            return rpm, tpm, int(time.time())
        except httpx.HTTPStatusError as e:
            logging.warning(f"Failed to fetch rate limits for {model}: {e}")
            return 60, 400000, int(time.time())  # Use default limits on failure
        except Exception as e:
            logging.error(f"Error fetching rate limits for {model}: {e}")
            return 60, 400000, int(time.time())  # Use default limits on failure

    def is_in_cooldown(self, model: str) -> bool:
        """
        Check if the rate limiter is in cooldown for a given model.
        
        Args:
            model: The model name.
            
        Returns:
            True if in cooldown, False otherwise.
        """
        if model not in self.limits:
            return False  # No limits set, not in cooldown

        _, _, last_reset_time = self.limits[model]
        cooldown_period = 60  # Cooldown period is 60 seconds

        return time.time() - last_reset_time < cooldown_period

    def check_limit(self, model: str, prompt: str) -> None:
        """
        Check if the rate limits for a given model have been exceeded.
        
        Args:
            model: The model name.
            prompt: The prompt to be sent to the model.
            
        Raises:
            Exception: If rate limits have been exceeded.
        """
        tokens = len(prompt.split())  # Rough token estimation
        now = int(time.time())

        if model not in self.limits:
            rpm, tpm, _ = self._get_limits(model)
            self.limits[model] = (rpm, tpm, now)
            self.usage[model] = (0, 0)  # Initialize usage

        rpm, tpm, last_reset_time = self.limits[model]
        tokens_used, requests_made = self.usage[model]

        # Reset limits if cooldown period has passed
        if now - last_reset_time >= 60:
            self.usage[model] = (0, 0)
            tokens_used, requests_made = 0, 0
            self.limits[model] = (rpm, tpm, now)

        if requests_made >= rpm:
            raise Exception(f"OpenRouter RPM limit exceeded for model {model}. Please try again in a minute.")
        if tokens_used + tokens >= tpm:
            raise Exception(f"OpenRouter TPM limit exceeded for model {model}. Please try again in a minute.")

        # Update usage
        self.usage[model] = (tokens_used + tokens, requests_made + 1)
        logging.info(f"OpenRouter Usage for {model}: {self.usage[model]}")


class OpenRouterClient:
    """Production-ready OpenRouter client with rate limiting"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.rate_limiter = RateLimiter()
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=60  # Increased timeout to 60 seconds
        )

    def generate_content(self, prompt: str, model: str = "meta-llama/Meta-Llama-3-8B-Instruct", retries: int = 3, **kwargs) -> str:
        """
        Generate content using OpenRouter's API with rate limiting and retries.
        
        Args:
            prompt: The prompt to be sent to the model.
            model: The model to use for content generation.
            retries: The number of retries in case of failure.
            **kwargs: Additional keyword arguments to pass to the API.
            
        Returns:
            The generated content.
            
        Raises:
            Exception: If content generation fails after multiple retries.
        """
        for attempt in range(retries):
            try:
                self.rate_limiter.check_limit(model, prompt)

                data = {
                    "model": model,
                    "prompt": prompt,
                    **kwargs,  # Pass through temperature, max_tokens, etc.
                }

                response = self.client.post("/chat/completions", json=data)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                
                response_json = response.json()
                return response_json["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError as e:
                logging.warning(f"OpenRouter API error (attempt {attempt + 1}/{retries}): {e}")
                if e.response.status_code == 429:  # Rate limit error
                    if self.rate_limiter.is_in_cooldown(model):
                        logging.info(f"In cooldown, waiting before retrying...")
                        time.sleep(10)  # Wait before retrying
                    else:
                        logging.warning("Rate limit exceeded but not in cooldown. This may indicate an issue with the rate limiter.")
                        time.sleep(5)  # Wait before retrying
                else:
                    logging.error(f"OpenRouter API error: {e}")
                    raise  # Re-raise the exception for non-rate-limit errors

            except Exception as e:
                logging.error(f"Error generating content (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(5)  # Wait before retrying

        raise Exception("Failed to generate content after multiple retries.")
"""OpenRouter API client with rate limiting."""
import time
import logging
from typing import Optional, Tuple
import httpx
from dewey.llm.exceptions import LLMError

