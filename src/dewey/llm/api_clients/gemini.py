from __future__ import annotations

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
        "gemini-2.0-flash-lite": {
            "rpm": 30,
            "tpm": 1000000,
            "rpd": 3000,
            "min_request_interval": 2,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 60
        },
        "gemini-2.0-flash": {
            "rpm": 15,
            "tpm": 1000000,
            "rpd": 1500,
            "min_request_interval": 5,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 120
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.RLock()
            cls._instance.request_windows = {}  # Model -> list of request timestamps
            cls._instance.daily_requests = {}  # Model -> count of daily requests
            cls._instance.daily_start_time = {}  # Model -> start time of daily window
            cls._instance.last_request_time = {}  # Model -> last request timestamp
            cls._instance.failure_counts = {}  # Model -> count of consecutive failures
            cls._instance.circuit_open_until = {}  # Model -> timestamp when circuit closes
            cls._instance.logger = logging.getLogger("RateLimiter")
        return cls._instance

    def configure(self, config: dict) -> None:
        """Update rate limits from configuration."""
        if "model_limits" in config:
            # Deep merge the model limits to preserve defaults
            for model, limits in config["model_limits"].items():
                if model in self.MODEL_LIMITS:
                    self.MODEL_LIMITS[model].update(limits)
                else:
                    self.MODEL_LIMITS[model] = limits
                    
            self.logger.info(f"Updated rate limits: {self.MODEL_LIMITS}")

    def _get_limits(self, model: str) -> tuple[int, int, int, float]:
        """Get RPM, TPM, RPD, and min_request_interval for given model."""
        model_key = model.lower()
        for key in self.MODEL_LIMITS:
            if key.lower() in model_key:
                limits = self.MODEL_LIMITS[key]
                rpm = limits.get("rpm", 15)
                tpm = limits.get("tpm", 1_000_000)
                rpd = limits.get("rpd", 1500)
                min_interval = limits.get("min_request_interval", 5)
                
                self.logger.debug(
                    f"Using limits for {key}: "
                    f"RPM={rpm}, TPM={tpm}, RPD={rpd}, "
                    f"min_interval={min_interval}s"
                )
                return rpm, tpm, rpd, min_interval
                
        self.logger.warning(
            f"No specific limits found for {model}, using defaults"
        )
        return (15, 1_000_000, 1500, 5)

    def _clean_request_window(self, model: str, now: float) -> None:
        """Remove requests older than 1 minute from the window and update daily counts."""
        if model in self.request_windows:
            # Keep track of requests within last minute for RPM
            self.request_windows[model] = [
                ts for ts in self.request_windows[model] 
                if now - ts < 60
            ]
            
            # Initialize or reset daily tracking if needed
            if model not in self.daily_start_time:
                self.daily_start_time[model] = now
                self.daily_requests[model] = 0
            elif now - self.daily_start_time[model] >= 86400:  # 24 hours passed
                self.daily_start_time[model] = now
                self.daily_requests[model] = 0

    def _get_usage_stats(self, model: str) -> dict:
        """Get current usage statistics."""
        now = time.time()
        if model in self.request_windows:
            current_rpm = len([ts for ts in self.request_windows[model] if now - ts < 60])
            daily_requests = self.daily_requests.get(model, 0)
            total_requests = len(self.request_windows[model])
            session_duration = (now - self.daily_start_time[model]) / 60  # in minutes
            avg_rpm = total_requests / max(1, session_duration)
            
            return {
                "current_rpm": current_rpm,
                "daily_requests": daily_requests,
                "total_requests": total_requests,
                "session_duration_mins": round(session_duration, 1),
                "avg_rpm": round(avg_rpm, 1)
            }
        return {}

    def _is_circuit_open(self, model: str, now: float) -> bool:
        """Check if circuit breaker is open for this model."""
        if model in self.circuit_open_until:
            if now < self.circuit_open_until[model]:
                return True
            # Circuit breaker timeout has elapsed, reset
            del self.circuit_open_until[model]
            self.failure_counts[model] = 0
        return False

    def _record_failure(self, model: str, now: float) -> None:
        """Record a failure and potentially open circuit breaker."""
        self.failure_counts[model] = self.failure_counts.get(model, 0) + 1
        
        # Get circuit breaker settings
        model_limits = next((limits for key, limits in self.MODEL_LIMITS.items() 
                           if key.lower() in model.lower()), self.MODEL_LIMITS["gemini-2.0-flash"])
        threshold = model_limits["circuit_breaker_threshold"]
        timeout = model_limits["circuit_breaker_timeout"]

        if self.failure_counts[model] >= threshold:
            self.circuit_open_until[model] = now + timeout
            self.logger.warning(
                f"🔌 Circuit breaker opened for {model} until "
                f"{time.strftime('%H:%M:%S', time.localtime(now + timeout))}"
            )

    def check_limit(self, model: str, prompt: str) -> None:
        """Check and enforce all rate limits with circuit breaking."""
        rpm, tpm, rpd, min_interval = self._get_limits(model)

        with self.lock:
            now = time.time()
            
            # Check circuit breaker first
            if model in self.circuit_open_until and now < self.circuit_open_until[model]:
                wait_time = self.circuit_open_until[model] - now
                msg = f"Circuit breaker open for {model} for {wait_time:.1f}s"
                raise LLMError(msg)

            # Initialize tracking for this model if needed
            if model not in self.request_windows:
                self.request_windows[model] = []
                self.daily_requests[model] = 0
                self.daily_start_time[model] = now
                self.failure_counts[model] = 0

            # Clean up old requests and reset daily counters if needed
            self.request_windows[model] = [
                ts for ts in self.request_windows[model] 
                if now - ts < 60  # Keep only last minute
            ]
            
            # Reset daily counter if 24 hours have passed
            if now - self.daily_start_time[model] >= 86400:
                self.daily_requests[model] = 0
                self.daily_start_time[model] = now
            
            try:
                # Check daily limit
                if self.daily_requests[model] >= rpd:
                    msg = f"Daily request limit ({rpd}) reached for {model}"
                    self._record_failure(model, now)
                    raise LLMError(msg)
                
                # Get current RPM from sliding window
                current_rpm = len([ts for ts in self.request_windows[model] if now - ts < 60])
                
                # Check RPM limit
                if current_rpm >= rpm:
                    msg = f"Rate limit ({rpm} requests/minute) exceeded for {model}"
                    self._record_failure(model, now)
                    raise LLMError(msg)
                
                # Get time since last request
                last_req_time = self.last_request_time.get(model, 0)
                time_since_last = now - last_req_time

                # Log current status
                self.logger.info(
                    f"Request #{self.daily_requests[model] + 1} | "
                    f"Current RPM: {current_rpm}/{rpm} | "
                    f"Daily: {self.daily_requests[model]}/{rpd} | "
                    f"Avg RPM: {current_rpm/max(1, (now - self.daily_start_time[model])/60):.1f}"
                )

                # If we're approaching RPM limit, add extra delay
                if current_rpm >= rpm - 2:
                    min_interval *= 1.5
                    self.logger.info(
                        f"⚠️  Approaching RPM limit, increasing delay to {min_interval:.1f}s"
                    )

                # Enforce minimum interval between requests
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    self.logger.info(f"⏳ Pacing requests... waiting {wait_time:.1f}s")
                    time.sleep(wait_time)

                # Update tracking AFTER all checks pass and delays
                self.request_windows[model].append(now)
                self.last_request_time[model] = now
                self.daily_requests[model] += 1
                
                # Reset failure count on successful request
                self.failure_counts[model] = 0
                
            except Exception as e:
                self._record_failure(model, now)
                raise


class GeminiClient:
    """Production-ready Google Gemini client with rate limiting."""

    def __init__(self, api_key: str | None = None, config: dict | None = None) -> None:
        load_dotenv()  # Ensure .env is loaded
        self.logger = logging.getLogger("GeminiClient")
        self.logger.setLevel(logging.INFO)
        
        """
        Initialize Gemini client with proper rate limiting.

        Args:
            api_key: Optional Gemini API key. Uses GEMINI_API_KEY env var if not provided.
            config: Configuration dictionary for model and rate limiting
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            msg = "Gemini API key not found. Set GEMINI_API_KEY environment variable."
            raise LLMError(msg)

        genai.configure(api_key=self.api_key)
        self.rate_limiter = RateLimiter()
        self.config = config or {}
        
        # Configure rate limiter with model limits from config
        if "model_limits" in self.config:
            self.rate_limiter.configure({"model_limits": self.config["model_limits"]})
        
        self.default_model = self.config.get("default_model", "gemini-2.0-flash-lite")
        self.fallback_model = self.config.get(
            "fallback_model", "gemini-2.0-flash-lite"
        )
        self.models = {}  # Cache for model instances
        self.logger.info(f"Initialized Gemini client with default model: {self.default_model}")

    def _get_model(self, model_name: str) -> genai.GenerativeModel:
        """Get or create a model instance."""
        if model_name not in self.models:
            self.models[model_name] = genai.GenerativeModel(model_name)
        return self.models[model_name]

    def generate_content(
        self,
        prompt: str,
        model: str | None = None,
        retries: int = 3,
        **kwargs,
    ) -> str:
        """Generate content with automatic rate limiting and token tracking."""
        model = model or self.default_model
        last_error = None
        backoff_time = 1.0

        for attempt in range(retries + 1):
            try:
                model_instance = self._get_model(model)
                
                generation_config = {
                    "temperature": kwargs.get("temperature", 0.7),
                }
                
                if "max_output_tokens" in kwargs:
                    generation_config["max_output_tokens"] = kwargs["max_output_tokens"]
                
                self.logger.info(
                    f"🔄 Generating content | "
                    f"Model: {model} | "
                    f"Temperature: {generation_config['temperature']} | "
                    f"Input length: {len(prompt.split())} words"
                    + (f" | Attempt: {attempt + 1}/{retries + 1}" if attempt > 0 else "")
                )
                
                # Enforce rate limits before making request
                try:
                    self.rate_limiter.check_limit(model, prompt)
                except LLMError as e:
                    if "Circuit breaker open" in str(e):
                        # If circuit breaker is open, try fallback model
                        if model != self.fallback_model and self.fallback_model:
                            self.logger.warning(
                                f"Circuit breaker open for {model}, "
                                f"trying fallback model {self.fallback_model}"
                            )
                            return self.generate_content(
                                prompt,
                                model=self.fallback_model,
                                retries=retries,
                                **kwargs
                            )
                    raise

                response = model_instance.generate_content(
                    contents=[prompt],
                    generation_config=genai.types.GenerationConfig(
                        **generation_config
                    ),
                )

                if not response.text:
                    msg = f"Empty response from Gemini API: {response.prompt_feedback}"
                    raise LLMError(msg)

                output_length = len(response.text.split())
                self.logger.info(
                    f"✅ Response received | "
                    f"Output length: {output_length} words"
                )

                return response.text

            except Exception as e:
                last_error = e
                
                # Don't retry if circuit breaker is open
                if isinstance(e, LLMError) and "Circuit breaker open" in str(e):
                    raise

                if attempt < retries:
                    # Add jitter to backoff
                    jitter = random.uniform(0.1, 0.5)
                    sleep_time = backoff_time + jitter
                    
                    self.logger.warning(
                        f"⚠️  Error on attempt {attempt + 1}/{retries + 1}: {str(e)} | "
                        f"Retrying in {sleep_time:.1f}s"
                    )
                    
                    time.sleep(sleep_time)
                    backoff_time *= 2  # Exponential backoff
                    
                    # Try fallback model if available and not already using it
                    if model != self.fallback_model and self.fallback_model:
                        self.logger.warning(
                            f"Switching to fallback model {self.fallback_model}"
                        )
                        return self.generate_content(
                            prompt,
                            model=self.fallback_model,
                            retries=retries,
                            **kwargs
                        )

        # If we get here, all retries failed
        self.logger.error(f"❌ All {retries + 1} attempts failed")
        msg = f"Gemini API error after {retries + 1} attempts: {last_error!s}"
        raise LLMError(msg) from last_error
