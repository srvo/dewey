from typing import Optional, Dict, Any, Tuple
import os
import time
import threading
import google.generativeai as genai
from dotenv import load_dotenv
from llm.exceptions import LLMError

# Load environment variables from .env file
load_dotenv()

class RateLimiter:
    """Enforce Gemini API rate limits dynamically based on model"""
    MODEL_LIMITS = {
        "gemini-2.0-flash": (15, 1_000_000, 1500),
        "gemini-2.0-flash-lite": (30, 1_000_000, 1500),
        "gemini-2.0-pro": (2, 1_000_000, 50),
        "gemini-2.0-flash-thinking": (10, 4_000_000, 1500),
        "gemini-1.5-flash": (15, 1_000_000, 1500),
        "gemini-1.5-flash-8b": (15, 1_000_000, 1500)
    }
    
    def __init__(self):
        self.lock = threading.Lock()
        self.counters = {}

    def _get_limits(self, model: str) -> Tuple[int, int, int]:
        """Get RPM, TPM, RPD for given model"""
        base_model = model.split("/")[-1].lower()
        return self.MODEL_LIMITS.get(base_model, (15, 100_000, 1500))  # Conservative defaults

    def check_limit(self, model: str, prompt: str) -> None:
        """Check and enforce rate limits with sleep if needed"""
        rpm, tpm, _ = self._get_limits(model)
        estimated_tokens = len(prompt.split()) * 1.33  # Rough token estimation
        
        with self.lock:
            now = time.time()
            
            # Initialize model tracking
            if model not in self.counters:
                self.counters[model] = {
                    'requests': [],
                    'tokens': 0,
                    'last_reset': now
                }
                
            # Reset counters if over 1 minute
            if now - self.counters[model]['last_reset'] > 60:
                self.counters[model]['requests'] = []
                self.counters[model]['tokens'] = 0
                self.counters[model]['last_reset'] = now
                
            # Check RPM
            if len(self.counters[model]['requests']) >= rpm:
                time.sleep(60 - (now - self.counters[model]['last_reset']))
                
            # Check TPM
            if self.counters[model]['tokens'] + estimated_tokens > tpm:
                time.sleep(60 - (now - self.counters[model]['last_reset']))
                
            # Update counters
            self.counters[model]['requests'].append(now)
            self.counters[model]['tokens'] += estimated_tokens

class GeminiClient:
    """Production-ready Google Gemini client with rate limiting"""
    
    def __init__(self, api_key: Optional[str] = None):
        load_dotenv()  # Ensure .env is loaded
        """
        Initialize Gemini client with proper rate limiting.
        
        Args:
            api_key: Optional Gemini API key. Uses GEMINI_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
            
        genai.configure(api_key=self.api_key)
        self.rate_limiter = RateLimiter()
        self.client = genai.GenerativeModel('gemini-pro')

    def generate_content(self, prompt: str, model: str = "gemini-2.0-flash", **kwargs) -> str:
        """
        Generate content with automatic rate limiting and token tracking.
        
        Args:
            prompt: Input text prompt
            model: Gemini model name
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text content
            
        Raises:
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
                        max_output_tokens=max_tokens,
                        **kwargs
                    )
                )
            except Exception as e:
                if "RPM" in str(e) or "rate limit" in str(e).lower():
                    self.logger.warning(f"Rate limit hit on {model}, falling back to flash-lite")
                    return self.generate_content(
                        prompt,
                        model="gemini-2.0-flash-lite",
                        **kwargs
                    )
                raise
            
            if not response.text:
                raise LLMError(f"Empty response from Gemini API: {response.prompt_feedback}")
                
            return response.text
            
        except Exception as e:
            raise LLMError(f"Gemini API error: {str(e)}") from e
