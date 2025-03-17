"""
DeepSeek Engine
==============

Core implementation of the DeepSeek API client.
Handles API communication, caching, and error management.

Features:
--------
1. API Communication: Managed access to DeepSeek endpoints
2. Context Caching: Performance optimization through context reuse
3. Error Handling: Robust error management and analysis
4. Rate Limiting: Controlled API access
5. Function Calling: Support for DeepSeek function calls
6. JSON Mode: Structured JSON output support
7. Multi-round Chat: Stateless conversation handling
8. Chat Prefix Completion: Assistant message completion (Beta)

API Documentation:
---------------
- Function Calling: https://api-docs.deepseek.com/guides/function_calling
- JSON Mode: https://api-docs.deepseek.com/guides/json_mode
- Multi-round Chat: https://api-docs.deepseek.com/guides/multi_round_chat
- Chat Prefix: https://api-docs.deepseek.com/guides/chat_prefix_completion
"""

from typing import List, Dict, Any, Set, Optional, TypedDict, Literal, Callable, Union
from ratelimit import limits, sleep_and_retry
from .base import AnalysisEngine, BaseEngine
import logging
from datetime import datetime
from dataclasses import dataclass
import json
import httpx
import re


class SearchResult(TypedDict):
    """Structure for input search results."""

    title: str
    snippet: str
    url: Optional[str]
    timestamp: Optional[str]


class CacheMetricsDict(TypedDict):
    """Structure for cache performance metrics."""

    hit_tokens: int
    miss_tokens: int
    total_requests: int


class FunctionCall(TypedDict):
    """Structure for function call data."""

    name: str
    arguments: str


class FunctionDefinition(TypedDict):
    """Structure for function definition."""

    name: str
    description: str
    parameters: Dict[str, Any]


class APIResponse(TypedDict):
    """Structure for API response data."""

    content: str
    cache_metrics: CacheMetricsDict
    error: Optional[str]
    function_call: Optional[FunctionCall]


class ConversationMessage(TypedDict):
    """Structure for conversation messages."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class CacheMetrics:
    """Track cache hit metrics for optimization."""

    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    total_requests: int = 0


@dataclass
class FunctionMetadata:
    """Metadata for registered functions."""

    handler: Callable
    definition: FunctionDefinition
    rate_limit: int = 60  # calls per minute
    last_call: float = 0.0
    call_count: int = 0


class ResponseFormat(TypedDict):
    """Structure for response format specification."""

    type: Literal["text", "json_object"]


class ChatOptions(TypedDict, total=False):
    """Structure for chat completion options."""

    model: str
    response_format: Optional[ResponseFormat]
    temperature: Optional[float]
    max_tokens: Optional[int]
    functions: Optional[List[Dict[str, Any]]]
    stop: Optional[List[str]]


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class DeepSeekEngine(BaseEngine, AnalysisEngine):
    """
    DeepSeek API client implementation.

    Features:
    - API Communication: Managed access to DeepSeek endpoints
    - Context Caching: Performance optimization through context reuse
    - Error Handling: Robust error management and analysis
    - Rate Limiting: Controlled API access
    - Function Calling: Support for DeepSeek function calls
    - JSON Mode: Structured JSON output support
    - Multi-round Chat: Stateless conversation handling
    - Chat Prefix Completion: Assistant message completion (Beta)
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        """Initialize the DeepSeek engine.
        
        Args:
            api_key: DeepSeek API key
            base_url: Base URL for the DeepSeek API
        """
        super().__init__()  # Initialize BaseEngine
        # Ensure API key has the correct format
        self.api_key = api_key if api_key.startswith("sk-") else f"sk-{api_key}"
        self.base_url = base_url.rstrip("/")
        self.templates: Dict[str, List[ConversationMessage]] = {}
        self.functions: Dict[str, FunctionMetadata] = {}
        self.cache_metrics = CacheMetrics()
        self.json_encoder = DateTimeEncoder
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )

    def register_function(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        rate_limit: int = 60,
    ) -> None:
        """
        Register a function for DeepSeek to call.

        Args:
            name: Function identifier
            description: Function description
            parameters: JSON Schema of parameters
            handler: Function to call
            rate_limit: Maximum calls per minute
        """
        self.functions[name] = FunctionMetadata(
            handler=handler,
            definition={
                "name": name,
                "description": description,
                "parameters": parameters,
            },
            rate_limit=rate_limit,
        )

    def get_function_definitions(self) -> List[FunctionDefinition]:
        """Get all registered function definitions."""
        return [f.definition for f in self.functions.values()]

    async def handle_function_call(self, function_call: FunctionCall) -> Any:
        """
        Execute a function call from DeepSeek.

        Args:
            function_call: Function call data

        Returns:
            Function result

        Raises:
            ValueError: If function not found or rate limited
        """
        name = function_call["name"]
        if name not in self.functions:
            raise ValueError(f"Function {name} not registered")

        metadata = self.functions[name]
        current_time = datetime.now().timestamp()

        # Check rate limit
        if (current_time - metadata.last_call) > 60:
            metadata.call_count = 0
            metadata.last_call = current_time
        elif metadata.call_count >= metadata.rate_limit:
            raise ValueError(f"Function {name} rate limit exceeded")

        # Update call stats
        metadata.call_count += 1
        metadata.last_call = current_time

        # Execute function
        try:
            args = json.loads(function_call["arguments"])
            return await metadata.handler(**args)
        except Exception as e:
            self.logger.error(f"Error executing function {name}: {str(e)}")
            raise

    def add_template(self, name: str, template: List[ConversationMessage]) -> None:
        """
        Store a conversation template.

        Args:
            name: Template identifier
            template: List of conversation messages
        """
        self.templates[name] = template

    def get_template(self, name: str) -> List[ConversationMessage]:
        """
        Retrieve a conversation template.

        Args:
            name: Template identifier

        Returns:
            Template messages or empty list if not found
        """
        return self.templates.get(name, [])

    def _update_cache_metrics(self, usage: Dict[str, int]) -> None:
        """Update cache performance metrics."""
        self.cache_metrics.total_requests += 1
        self.cache_metrics.prompt_cache_hit_tokens += usage.get(
            "prompt_cache_hit_tokens", 0
        )
        self.cache_metrics.prompt_cache_miss_tokens += usage.get(
            "prompt_cache_miss_tokens", 0
        )

    @sleep_and_retry
    @limits(calls=25, period=60)  # Limit to 25 calls per minute
    async def _send_single_request(self, messages: List[ConversationMessage], **kwargs) -> APIResponse:
        """Send a single request to the DeepSeek API."""
        try:
            # Convert request to JSON using custom encoder
            request_data = {
                "model": "deepseek-chat",
                "messages": messages,
                **kwargs
            }
            json_data = json.dumps(request_data, cls=self.json_encoder)
            
            # Log request using base method
            self._log_api_request(
                method="POST",
                url=f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=request_data
            )
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        content=json_data,
                        timeout=30.0,
                    )
                    
                    if response.status_code != 200:
                        error_msg = f"API request failed: {response.status_code} - {response.text}"
                        self.logger.error(error_msg)
                        return {
                            "content": "",
                            "cache_metrics": {"hit_tokens": 0, "miss_tokens": 0, "total_requests": 1},
                            "error": error_msg,
                            "function_call": None
                        }
                    
                    try:
                        data = response.json()
                        # Log response using base method
                        self._log_api_response(
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            data=data
                        )
                        
                        return {
                            "content": data["choices"][0]["message"]["content"],
                            "cache_metrics": data.get("cache_metrics", {"hit_tokens": 0, "miss_tokens": 0, "total_requests": 1}),
                            "error": None,
                            "function_call": data["choices"][0]["message"].get("function_call")
                        }
                    except Exception as e:
                        error_msg = f"Failed to parse API response: {str(e)}"
                        self.logger.error(error_msg)
                        self.logger.error(f"Raw response: {response.text}")
                        return {
                            "content": "",
                            "cache_metrics": {"hit_tokens": 0, "miss_tokens": 0, "total_requests": 1},
                            "error": error_msg,
                            "function_call": None
                        }
                except httpx.RequestError as e:
                    error_msg = f"HTTP request failed: {str(e)}"
                    self.logger.error(error_msg)
                    return {
                        "content": "",
                        "cache_metrics": {"hit_tokens": 0, "miss_tokens": 0, "total_requests": 1},
                        "error": error_msg,
                        "function_call": None
                    }
        except Exception as e:
            error_msg = f"Unexpected error in API request: {str(e)}"
            self.logger.error(error_msg)
            return {
                "content": "",
                "cache_metrics": {"hit_tokens": 0, "miss_tokens": 0, "total_requests": 1},
                "error": error_msg,
                "function_call": None
            }

    async def json_completion(
        self,
        messages: List[ConversationMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> APIResponse:
        """
        Get a completion that returns valid JSON.
        
        Following DeepSeek's JSON mode requirements:
        1. Sets response_format to {"type": "json_object"}
        2. Ensures messages include JSON format instructions
        3. Sets reasonable max_tokens to prevent truncation
        
        Args:
            messages: List of conversation messages
            max_tokens: Maximum tokens in response
            temperature: Temperature for sampling
            **kwargs: Additional API parameters
            
        Returns:
            API response with JSON content
        """
        # Ensure system message includes JSON instructions
        has_system = any(m["role"] == "system" for m in messages)
        if not has_system:
            messages.insert(0, {
                "role": "system",
                "content": "You are a helpful assistant that ONLY outputs valid JSON. Do not include any explanatory text or comments outside the JSON object."
            })
        
        # Add JSON format requirement to user message if not present
        last_user_msg = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if last_user_msg and "json" not in last_user_msg["content"].lower():
            last_user_msg["content"] += "\n\nRespond with ONLY a valid JSON object."
        
        # Set JSON response format
        kwargs["response_format"] = {"type": "json_object"}
        
        # Set reasonable defaults
        if max_tokens is None:
            max_tokens = 2000  # Default to 2000 tokens for JSON responses
        kwargs["max_tokens"] = max_tokens
        
        if temperature is not None:
            kwargs["temperature"] = temperature
        
        return await self._send_single_request(messages, **kwargs)

    async def chat_completion(
        self,
        messages: List[ConversationMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> APIResponse:
        """Get a standard chat completion."""
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await self._send_single_request(messages, **kwargs)

    async def chat_prefix_completion(
        self, messages: List[ConversationMessage], stop: Optional[List[str]] = None
    ) -> APIResponse:
        """
        Make a chat prefix completion call (Beta).

        Args:
            messages: Messages with assistant prefix (set prefix=True)
            stop: Optional stop sequences

        Returns:
            API response with completion

        Example:
            ```python
            response = await engine.chat_prefix_completion([
                {"role": "user", "content": "Write Python code"},
                {"role": "assistant", "content": "```python\\n", "prefix": True}
            ], stop=["```"])
            ```
        """
        return await self.chat_completion(messages=messages, options={"stop": stop})

    async def _handle_api_error(
        self, error: Exception, messages: List[ConversationMessage]
    ) -> None:
        """
        Handle API errors with analysis.

        Args:
            error: Exception that occurred
            messages: Messages that caused the error
        """
        try:
            error_context = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "messages": messages,
            }

            error_messages = [
                {
                    "role": "system",
                    "content": "You are an API error analysis specialist.",
                },
                {
                    "role": "user",
                    "content": f"Analyze this API error and suggest solutions: {json.dumps(error_context)}",
                },
            ]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={"Authorization": self.api_key},
                    json={"model": "deepseek-chat", "messages": error_messages},
                )

                if response.status_code == 200:
                    analysis = response.json()["choices"][0]["message"]["content"]
                    self.logger.error(f"API Error Analysis:\n{analysis}")

        except Exception as e:
            self.logger.error(f"Error in error analysis: {str(e)}")
            self.logger.error(f"Original error: {str(error)}")

    async def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a set of results using DeepSeek.

        Implementation of the abstract method from AnalysisEngine.
        Uses chat completion with ethical analysis template.

        Args:
            results: List of dictionaries containing data to analyze

        Returns:
            Dictionary containing:
            - content: Analysis text
            - source: 'deepseek'
            - timestamp: ISO format timestamp
            - concerns_found: List of identified concerns
            - cache_metrics: Performance data
        """
        # Convert results to search result format
        search_results = [
            {
                "title": r.get("title", "Untitled"),
                "snippet": r.get("content", r.get("snippet", "")),
                "url": r.get("url", r.get("link", None)),
                "timestamp": r.get("timestamp", None),
            }
            for r in results
        ]

        # Build analysis messages
        messages = []
        if "ethical_analysis" in self.templates:
            messages.extend(self.templates["ethical_analysis"])

        # Add results context
        snippets = "\n".join(
            [f"- {r['title']}: {r['snippet']}" for r in search_results]
        )
        messages.append(
            {
                "role": "user",
                "content": f"""Analyze these search results for ethical concerns:

{snippets}

Please provide:
1. Main ethical concerns identified
2. Evidence and sources
3. Pattern of behavior
4. Severity assessment
5. Timeline of issues
6. Company's response""",
            }
        )

        # Get analysis
        response = await self.chat_completion(messages=messages)

        # Extract concerns
        concerns = set()
        if not response["error"] and response["content"]:
            content_lower = response["content"].lower()
            concern_mapping = {
                "environmental": "Environmental violations",
                "labor": "Labor rights issues",
                "safety": "Safety concerns",
                "governance": "Corporate governance issues",
                "animal": "Animal welfare concerns",
                "ethical": "Ethical misconduct",
                "regulatory": "Regulatory compliance issues",
                "social": "Social responsibility concerns",
            }
            for keyword, concern in concern_mapping.items():
                if keyword in content_lower:
                    concerns.add(concern)

        return {
            "content": response["content"],
            "source": "deepseek",
            "timestamp": datetime.now().isoformat(),
            "concerns_found": sorted(list(concerns)),
            "cache_metrics": response["cache_metrics"],
        }

    async def process(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Process text using the DeepSeek engine.
        
        Args:
            text: Text to process
            **kwargs: Additional processing parameters
            
        Returns:
            Dictionary containing processed results
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that processes text and provides structured analysis."
            },
            {
                "role": "user",
                "content": text
            }
        ]
        
        response = await self.chat_completion(messages=messages, **kwargs)
        return {
            "content": response["content"],
            "source": "deepseek",
            "timestamp": datetime.now().isoformat(),
            "error": response["error"],
            "cache_metrics": response["cache_metrics"]
        }
