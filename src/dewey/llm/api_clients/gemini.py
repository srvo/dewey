import logging
import os
import random
import threading
import time

import google.generativeai as genai
from dotenv import load_dotenv

from dewey.llm.exceptions import LLMError

# Load environment variables from .env file
load_dotenv()


class RateLimiter:
    """Global rate limiter singleton to track usage across instances."""

    _instance = None
    MODEL_LIMITS = {
        "gemini-2.0-flash": (15, 1_000_000, 1500),  # RPM, TPM, RPD
        "gemini-2.0-flash-lite": (30, 1_000_000, 1500),  # Higher RPM limit
        "gemini-2.0-pro": (2, 1_000_000, 50),
        "gemini-2.0-flash-thinking": (10, 4_000_000, 1500),
        "gemini-1.5-flash": (15, 1_000_000, 1500),
        "gemini-1.5-flash-8b": (15, 1_000_000, 1500),
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.RLock()
            cls._instance.counters = {}
            cls._instance.cooldowns = {}  # model: resume_time
            cls._instance.logger = logging.getLogger("RateLimiter")
            cls._instance.cooldown_minutes = 5  # Default, will be overridden by config
        return cls._instance

    def _get_limits(self, model: str) -> tuple[int, int, int]:
        """Get RPM, TPM, RPD for given model."""
        base_model = model.split("/")[-1].lower()
        return self.MODEL_LIMITS.get(
            base_model,
            (15, 100_000, 1500),
        )  # Conservative defaults

    def is_in_cooldown(self, model: str) -> bool:
        """Check if model is in cooldown period."""
        return model in self.cooldowns and time.time() < self.cooldowns[model]

    def check_limit(self, model: str, prompt: str) -> None:
        """Check and enforce all rate limits with exponential backoff."""
        # Check cooldown first
        if self.is_in_cooldown(model):
            msg = f"Model {model} in cooldown until {time.ctime(self.cooldowns[model])}"
            raise LLMError(
                msg,
            )

        rpm, tpm, rpd = self._get_limits(model)
        estimated_tokens = len(prompt.split()) * 1.33  # Token estimation

        with self.lock:
            now = time.time()
            model_counters = self.counters.setdefault(
                model,
                {
                    "requests": [],
                    "tokens": 0,
                    "daily_requests": 0,
                    "last_reset": now,
                    "daily_reset": now,
                },
            )

            # Reset minute counters
            if now - model_counters["last_reset"] > 60:
                model_counters["requests"] = []
                model_counters["tokens"] = 0
                model_counters["last_reset"] = now

            # Reset daily counters
            if now - model_counters["daily_reset"] > 86400:  # 24 hours
                model_counters["daily_requests"] = 0
                model_counters["daily_reset"] = now

            # Check and enforce RPM
            max_retries = 3
            for attempt in range(max_retries):
                current_time = time.time()
                remaining = 60 - (current_time - model_counters["last_reset"])
                current_rpm = len(model_counters["requests"])

                # If over RPM limit, wait with exponential backoff
                if current_rpm >= rpm:
                    wait_time = min(
                        remaining + 0.5,
                        (2**attempt) + (random.random() * 0.1),
                        60,
                    )  # Max 60 seconds
                    self.logger.warning(
                        f"RPM limit reached for {model}. Waiting {wait_time:.2f}s (attempt {attempt+1})",
                    )
                    time.sleep(wait_time)
                    continue

                # Check TPM limit
                if (model_counters["tokens"] + estimated_tokens) > tpm:
                    wait_time = min(
                        remaining + 0.5,
                        (2**attempt) + (random.random() * 0.1),
                    )
                    self.logger.warning(
                        f"TPM limit reached for {model}. Waiting {wait_time:.2f}s (attempt {attempt+1})",
                    )
                    time.sleep(wait_time)
                    continue

                # Check RPD limit
                if model_counters["daily_requests"] >= rpd:
                    msg = f"Daily request limit ({rpd}) reached for {model}"
                    raise LLMError(msg)

                # All checks passed, update counters
                model_counters["requests"].append(time.time())
                model_counters["tokens"] += estimated_tokens
                model_counters["daily_requests"] += 1
                return

            # Put model in cooldown if all retries failed
            self.cooldowns[model] = time.time() + (60 * self.cooldown_minutes)
            msg = f"Model {model} rate limited. Cooling down for {self.cooldown_minutes} minutes."
            raise LLMError(
                msg,
            )


class GeminiClient:
    """Production-ready Google Gemini client with rate limiting."""

    def __init__(self, api_key: str | None = None) -> None:
        load_dotenv()  # Ensure .env is loaded
        self.logger = logging.getLogger("GeminiClient")
        """
        Initialize Gemini client with proper rate limiting.

        Args:
            api_key: Optional Gemini API key. Uses GEMINI_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            msg = "Gemini API key not found. Set GEMINI_API_KEY environment variable."
            raise LLMError(
                msg,
            )

        genai.configure(api_key=self.api_key)
        self.rate_limiter = RateLimiter()
        self.client = genai.GenerativeModel("gemini-2.0-flash")

    def generate_content(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash",
        retries: int = 3,
        **kwargs,
    ) -> str:
        """Generate content with automatic rate limiting and token tracking.

        Args:
        ----
            prompt: Input text prompt
            model: Gemini model name
            **kwargs: Additional generation parameters

        Returns:
        -------
            Generated text content

        Raises:
        ------
            LLMError: For API errors or rate limit violations

        """
        try:
            # Enforce rate limits before making request
            self.rate_limiter.check_limit(model, prompt)

            try:
                response = self.client.generate_content(
                    contents=[prompt],
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        **kwargs,
                    ),
                )
            except Exception as e:
                if "RPM" in str(e) or "rate limit" in str(e).lower():
                    logging.warning(
                        f"Rate limit hit on {model}, falling back to 2.0-flash-lite",
                    )
                    return self.generate_content(
                        prompt,
                        model="gemini-2.0-flash-lite",  # Higher RPM limit model
                        **kwargs,
                    )
                raise

            if not response.text:
                msg = f"Empty response from Gemini API: {response.prompt_feedback}"
                raise LLMError(
                    msg,
                )

            return response.text

        except Exception as e:
            if retries > 0 and "429" in str(e):
                jitter = random.uniform(0.1, 55)
                backoff = (2 ** (3 - retries)) + jitter
                self.logger.warning(
                    f"API error: {e!s}. Retrying in {backoff:.2f}s ({retries} left)",
                )
                time.sleep(backoff)
                return self.generate_content(
                    prompt,
                    model=model,
                    retries=retries - 1,
                    **kwargs,
                )

            # Add model to cooldown if quota exhausted
            if "quota" in str(e).lower():
                self.rate_limiter.cooldowns[model] = time.time() + (
                    self.rate_limiter.cooldown_minutes * 60
                )
                self.logger.exception(
                    f"Quota exhausted for {model}, cooling down for {self.rate_limiter.cooldown_minutes} minutes",
                )

            msg = f"Gemini API error: {e!s}"
            raise LLMError(msg) from e
