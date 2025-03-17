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
        "gemini-2.0-flash": {
            "rpm": 15,
            "tpm": 1000000,
            "rpd": 1500,
            "min_request_interval": 4,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 120
        },
        "gemini-2.0-flash-lite": {
            "rpm": 30,
            "tpm": 1000000,
            "rpd": 1500,
            "min_request_interval": 2,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 60
        },
        "gemini-2.0-pro-experimental-02-05": {
            "rpm": 2,
            "tpm": 1000000,
            "rpd": 50,
            "min_request_interval": 30,
            "circuit_breaker_threshold": 2,
            "circuit_breaker_timeout": 300
        },
        "gemini-2.0-flash-thinking-exp-01-21": {
            "rpm": 10,
            "tpm": 4000000,
            "rpd": 1500,
            "min_request_interval": 6,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 180
        },
        "gemini-1.5-flash": {
            "rpm": 15,
            "tpm": 1000000,
            "rpd": 1500,
            "min_request_interval": 4,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 120
        },
        "gemini-1.5-flash-8b": {
            "rpm": 15,
            "tpm": 1000000,
            "rpd": 1500,
            "min_request_interval": 4,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 120
        },
        "gemini-1.5-pro": {
            "rpm": 2,
            "tpm": 32000,
            "rpd": 50,
            "min_request_interval": 30,
            "circuit_breaker_threshold": 2,
            "circuit_breaker_timeout": 300
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

    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-pro-experimental-02-05",
        "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro"
    ]

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
        self.context_cache = {}  # Cache for context windows
        self.logger.info(f"Initialized Gemini client with default model: {self.default_model}")

    def _get_model(self, model_name: str) -> genai.GenerativeModel:
        """Get or create a model instance."""
        if model_name not in self.models:
            self.models[model_name] = genai.GenerativeModel(model_name)
        return self.models[model_name]

    def _save_llm_output(self, prompt: str, response: str, model: str, metadata: dict | None = None) -> None:
        """Save LLM interaction to a log file for later reference.
        
        Args:
            prompt: The input prompt
            response: The LLM's response
            model: The model used
            metadata: Optional additional metadata about the request
        """
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            
            # Get project root from environment or default to current directory
            project_root = os.getenv("DEWEY_PROJECT_ROOT", os.getcwd())
            
            # Create docs/llm_outputs directory if it doesn't exist
            output_dir = Path(project_root) / "docs" / "llm_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_file = output_dir / f"llm_output_{timestamp}.json"
            
            # Prepare output data
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "prompt": prompt,
                "response": response,
                "metadata": metadata or {}
            }
            
            # Save to file
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
                
            self.logger.debug(f"Saved LLM output to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save LLM output: {e}")

    def generate_content(
        self,
        prompt: str,
        model: str | None = None,
        retries: int = 3,
        enable_code_execution: bool = False,
        cache_context: bool = False,
        cache_key: str | None = None,
        media_inputs: list | None = None,
        **kwargs,
    ) -> str:
        """
        Generate content using Gemini model with support for code execution and context caching.

        Args:
            prompt: The prompt to send to the model
            model: Optional model override (defaults to self.default_model)
            retries: Number of retries on failure
            enable_code_execution: Whether to enable code execution tools
            cache_context: Whether to cache the context for reuse
            cache_key: Key to use for context caching (required if cache_context=True)
            media_inputs: List of media inputs (images, video, audio) to include
            **kwargs: Additional arguments passed to the model

        Returns:
            Generated content as string
        """
        model = model or self.default_model
        attempt = 0
        last_error = None
        
        # Configure tools if code execution is enabled
        if enable_code_execution:
            kwargs["tools"] = [{"code_execution": {}}]
        
        # Handle context caching
        if cache_context:
            if not cache_key:
                raise ValueError("cache_key is required when cache_context=True")
            
            if cache_key in self.context_cache:
                # Use cached context
                self.logger.info(f"Using cached context for key: {cache_key}")
                kwargs["context"] = self.context_cache[cache_key]
            else:
                # Cache new context
                self.context_cache[cache_key] = prompt
                self.logger.info(f"Caching new context with key: {cache_key}")

        # Handle media inputs
        if media_inputs:
            contents = []
            for media in media_inputs:
                if isinstance(media, (str, bytes)):
                    # Handle raw media data
                    contents.append({"media": media})
                elif isinstance(media, dict):
                    # Handle pre-formatted media input
                    contents.append(media)
            contents.append({"text": prompt})
            kwargs["contents"] = contents
        else:
            kwargs["contents"] = prompt

        while attempt < retries:
            try:
                # Check rate limits before making request
                try:
                    self.rate_limiter.check_limit(model, prompt)
                except LLMError as e:
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "circuit breaker" in error_msg or "resource has been exhausted" in error_msg:
                        # Always prompt to switch to DeepInfra on first rate limit error
                        from rich.prompt import Confirm
                        if Confirm.ask(
                            "[yellow]Gemini API is rate limited. Would you like to switch to DeepInfra?[/yellow]"
                        ):
                            self.logger.info("Switching to DeepInfra...")
                            return self._use_deepinfra_fallback(prompt, **kwargs)
                        # If user declines, continue with retries
                    raise

                # Get model instance
                model_instance = self._get_model(model)
                
                # Remove unsupported parameters
                kwargs.pop('temperature', None)  # Gemini doesn't support temperature
                kwargs.pop('response_format', None)  # Gemini doesn't support response_format
                
                # Generate response
                response = model_instance.generate_content(**kwargs)
                
                # Handle code execution results
                if enable_code_execution and hasattr(response, "candidates"):
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if hasattr(part, "code_execution_result"):
                                self.logger.info("Code execution result received")
                                result = part.code_execution_result.output
                                # Save the output
                                self._save_llm_output(
                                    prompt=prompt,
                                    response=result,
                                    model=model,
                                    metadata={
                                        "type": "code_execution",
                                        "attempt": attempt + 1,
                                        "kwargs": {k: str(v) for k, v in kwargs.items()}
                                    }
                                )
                                return result
                
                # Get text response
                result = response.text
                
                # Save the output
                self._save_llm_output(
                    prompt=prompt,
                    response=result,
                    model=model,
                    metadata={
                        "attempt": attempt + 1,
                        "kwargs": {k: str(v) for k, v in kwargs.items()}
                    }
                )
                
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                # Check for rate limit errors in the exception
                if "rate limit" in error_msg or "circuit breaker" in error_msg or "resource has been exhausted" in error_msg:
                    # Prompt to switch to DeepInfra on rate limit errors
                    from rich.prompt import Confirm
                    if Confirm.ask(
                        "[yellow]Gemini API is rate limited. Would you like to switch to DeepInfra?[/yellow]"
                    ):
                        self.logger.info("Switching to DeepInfra...")
                        return self._use_deepinfra_fallback(prompt, **kwargs)
                
                attempt += 1
                last_error = e
                
                if attempt < retries:
                    # Add jitter to retry delay
                    delay = (2 ** attempt) + random.uniform(0.1, 0.5)
                    self.logger.warning(
                        f"Attempt {attempt} failed: {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    
                    # Try fallback model on last attempt
                    if attempt == retries - 1 and model != self.fallback_model:
                        self.logger.info(f"Trying fallback model: {self.fallback_model}")
                        model = self.fallback_model
                else:
                    msg = f"Failed after {retries} attempts. Last error: {str(last_error)}"
                    raise LLMError(msg)
                    
        msg = f"Failed after {retries} attempts. Last error: {str(last_error)}"
        raise LLMError(msg)

    def _use_deepinfra_fallback(self, prompt: str, **kwargs) -> str:
        """Switch to DeepInfra's models as a fallback."""
        try:
            # Import DeepInfra client only when needed
            from dewey.llm.api_clients.deepinfra import DeepInfraClient
            
            # Initialize DeepInfra client
            deepinfra_client = DeepInfraClient()
            
            # Map Gemini parameters to DeepInfra parameters
            deepinfra_kwargs = {
                "model": "google/gemini-2.0-flash-001",  # Use DeepInfra's Gemini model
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1024),
            }
            
            self.logger.info("Using DeepInfra as fallback")
            return deepinfra_client.generate_content(prompt, **deepinfra_kwargs)

        except Exception as e:
            self.logger.error(f"DeepInfra fallback failed: {e}")
            raise LLMError("Both Gemini and DeepInfra fallback failed") from e

    def clear_context_cache(self, cache_key: str | None = None) -> None:
        """
        Clear the context cache.

        Args:
            cache_key: Optional specific cache key to clear. If None, clears entire cache.
        """
        if cache_key:
            if cache_key in self.context_cache:
                del self.context_cache[cache_key]
                self.logger.info(f"Cleared cache for key: {cache_key}")
        else:
            self.context_cache.clear()
            self.logger.info("Cleared entire context cache")
