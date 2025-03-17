from __future__ import annotations

import os
import logging

from openai import OpenAI
from dotenv import load_dotenv

from dewey.llm.exceptions import LLMError


class DeepInfraClient:
    """Client for interacting with DeepInfra's OpenAI-compatible API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize DeepInfra client.

        Args:
        ----
            api_key: Optional DeepInfra API key. If not provided, will attempt
                to read from DEEPINFRA_API_KEY environment variable.

        """
        # Load environment variables from project root .env
        env_path = os.path.join(os.getenv("DEWEY_PROJECT_ROOT", "/Users/srvo/dewey"), ".env")
        load_dotenv(env_path)
        
        # Try to get API key from parameter first, then environment
        self.api_key = api_key or os.getenv("DEEPINFRA_API_KEY")
        logging.info(f"Using API key: {self.api_key}")
        
        if not self.api_key:
            msg = f"DeepInfra API key not found in environment file at {env_path}. Set DEEPINFRA_API_KEY in .env file."
            raise LLMError(msg)
        
        # Initialize OpenAI client with proper configuration
        self.client = OpenAI(
            base_url="https://api.deepinfra.com/v1/openai",
            api_key=self.api_key,
            default_headers={"Content-Type": "application/json"}
        )
        logging.info("OpenAI client initialized with DeepInfra configuration")

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
                
            logging.debug(f"Saved LLM output to {output_file}")
            
        except Exception as e:
            logging.warning(f"Failed to save LLM output: {e}")

    def chat_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_message: str | None = None,
        **kwargs,
    ) -> str:
        """Generate a chat completion response from DeepInfra.

        Args:
        ----
            prompt: User input prompt
            model: Model identifier string (e.g. "google/gemini-2.0-flash-001")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_message: Optional system message to guide model behavior
            **kwargs: Additional parameters for completion

        Returns:
        -------
            Generated text content as a string

        Note:
        ----
            When using Gemini models via DeepInfra, use these model identifiers:
            - google/gemini-2.0-flash-001: Latest Gemini model (recommended)
            - google/gemini-2.0-pro: Base Gemini model
            - google/gemini-2.0-pro-vision: Multimodal Gemini model
        """
        messages = []
        
        # Add JSON formatting instructions to system message if needed
        if "response_format" in kwargs:
            base_system = system_message or ""
            json_system = f"""CRITICAL: You must return ONLY a valid JSON object with NO additional text or formatting.

Rules:
1. NO markdown code blocks or backticks
2. NO explanatory text before or after the JSON
3. ALL property names must be in double quotes
4. ALL string values must be in double quotes
5. NO trailing commas
6. NO comments in the JSON
7. Escape all quotes within strings
8. NO line breaks within string values

Format: {kwargs['response_format']}

{base_system}"""
            messages.append({"role": "system", "content": json_system})
        elif system_message:
            messages.append({"role": "system", "content": system_message})
            
        messages.append({"role": "user", "content": prompt})

        try:
            # Ensure model name is correct for Gemini
            if "gemini" in model.lower() and not model.startswith("google/"):
                model = f"google/{model}"

            # Log request details
            logger = logging.getLogger("DeepInfraClient")
            logger.info(f"🤖 Generating response using {model}")
            logger.info(f"⚙️  Parameters: temp={temperature:.1f}, max_tokens={max_tokens}")
            
            # Track request timing
            import time
            start_time = time.time()

            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            except Exception as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    logger.error("❌ Rate limit exceeded. Consider implementing backoff.")
                    raise LLMError("DeepInfra rate limit exceeded. Please try again in a few seconds.") from e
                raise  # Re-raise other exceptions
            
            # Calculate timing
            duration = time.time() - start_time
            
            # Extract the content from the response
            result = response.choices[0].message.content
            
            # Clean up JSON response if needed
            if "response_format" in kwargs:
                import json
                import re
                
                # Remove any markdown formatting
                result = result.strip()
                if result.startswith("```json"):
                    result = result[7:]
                elif result.startswith("```"):
                    result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]
                result = result.strip()
                
                # Remove any comments
                result = re.sub(r'//.*?\n|/\*.*?\*/', '', result, flags=re.DOTALL)
                
                # Fix common JSON formatting issues
                result = re.sub(r',(\s*[}\]])', r'\1', result)  # Remove trailing commas
                result = re.sub(r'(?<!\\)"(?![:,}\]])', '\\"', result)  # Escape unescaped quotes in values
                result = re.sub(r'[\n\r]+', ' ', result)  # Remove line breaks in strings
                
                # Try to parse and re-serialize to ensure valid JSON
                try:
                    parsed = json.loads(result)
                    result = json.dumps(parsed)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON response: {e}")
                    logger.error(f"Raw response: {result}")
                    # Try to extract just the JSON object/array
                    json_match = re.search(r'({[\s\S]*}|\[[\s\S]*\])', result)
                    if json_match:
                        try:
                            extracted = json_match.group(0)
                            parsed = json.loads(extracted)
                            result = json.dumps(parsed)
                        except json.JSONDecodeError:
                            raise LLMError(f"Invalid JSON response: {e}")
                    else:
                        raise LLMError(f"Invalid JSON response: {e}")
            
            # Log completion details
            logger.info(f"✅ Response generated in {duration:.2f}s")
            logger.info(f"📊 Tokens: {response.usage.prompt_tokens} prompt + {response.usage.completion_tokens} completion = {response.usage.total_tokens} total")
            
            # Save the output
            self._save_llm_output(
                prompt=prompt,
                response=result,
                model=model,
                metadata={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "system_message": system_message,
                    "duration_seconds": duration,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "kwargs": {k: str(v) for k, v in kwargs.items()}
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ DeepInfra API error: {e!s}")
            msg = f"DeepInfra API error: {e!s}"
            raise LLMError(msg) from e

    def stream_completion(self, **kwargs) -> str:
        """Streaming version of chat completion (not yet implemented)."""
        msg = "Streaming completion not implemented yet"
        raise NotImplementedError(msg)

    def generate_content(
        self,
        prompt: str,
        model: str = "google/gemini-2.0-flash-001",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> str:
        """Generate content using DeepInfra's API. This is an alias for chat_completion
        to maintain compatibility with the Gemini client interface.

        Args:
            prompt: User input prompt
            model: Model identifier string (must start with "google/" for Gemini models)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for completion

        Returns:
            Generated text content as a string
        """
        return self.chat_completion(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
