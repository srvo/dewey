from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional
import json
from openai import OpenAI, AsyncOpenAI
from .models import (
    CompletionRequest,
    CompletionResponse,
    FunctionCallResponse,
    FIMRequest
)

class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, request: CompletionRequest
    ) -> CompletionResponse:
        """Synchronous completion"""
        pass

    @abstractmethod
    async def complete_stream(
        self, request: CompletionRequest
    ) -> AsyncGenerator[CompletionResponse, None]:
        """Streaming completion"""
        pass

    @abstractmethod
    async def fim_complete(
        self, request: FIMRequest
    ) -> CompletionResponse:
        """Fill-in-the-middle completion"""
        pass

class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, api_base: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.api_base = api_base
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        self._cache = {}  # Simple in-memory cache for context

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send completion request to DeepSeek API"""
        payload = self._prepare_payload(request)
        
        # Check cache if cache_id provided
        if request.cache_id and request.cache_id in self._cache:
            payload["cache_id"] = request.cache_id
        
        print(f"Request payload: {json.dumps(payload, indent=2)}")
        
        response = await self.client.chat.completions.create(**payload)
        print(f"Response: {response}")
        
        # Update cache if needed
        if request.cache_id:
            self._cache[request.cache_id] = getattr(response, "cache_id", None)
            
        return self._parse_response(response)

    async def complete_stream(
        self, request: CompletionRequest
    ) -> AsyncGenerator[CompletionResponse, None]:
        """Stream completion from DeepSeek API"""
        payload = self._prepare_payload(request, stream=True)
        
        if request.cache_id and request.cache_id in self._cache:
            payload["cache_id"] = request.cache_id
        
        async for chunk in await self.client.chat.completions.create(**payload):
            yield self._parse_response(chunk)

    async def fim_complete(self, request: FIMRequest) -> CompletionResponse:
        """Fill-in-the-middle completion"""
        payload = {
            "model": "deepseek-fim",
            "prompt": request.prompt,
            "suffix": request.suffix,
            "max_tokens": request.max_tokens
        }
        
        response = await self.client.completions.create(**payload)
        return self._parse_response(response)

    def _prepare_payload(
        self, request: CompletionRequest, stream: bool = False
    ) -> Dict[str, Any]:
        """Prepare the payload for the API request."""
        messages = []
        for msg in request.messages:
            message = {
                "role": msg.role,
                "content": msg.content if not msg.prefix else None,
                **({"name": msg.name} if msg.name else {}),
                **({"function_call": msg.function_call} if msg.function_call else {})
            }
            if msg.prefix:
                message["prefix"] = True
            messages.append(message)

        payload = {
            "model": request.config.model_name,
            "messages": messages,
            "temperature": request.config.temperature,
            "stream": stream
        }

        if request.config.functions:
            payload["functions"] = request.config.functions

        if request.config.max_tokens:
            payload["max_tokens"] = request.config.max_tokens

        if request.config.top_p:
            payload["top_p"] = request.config.top_p

        if request.config.stop:
            payload["stop"] = request.config.stop

        if request.config.use_beta:
            payload["beta"] = True

        return payload

    def _parse_response(self, response) -> CompletionResponse:
        """Parse DeepSeek API response"""
        choice = response.choices[0]
        message = choice.message
        
        function_call = None
        if hasattr(message, "function_call") and message.function_call is not None:
            function_call = FunctionCallResponse(
                name=message.function_call.name,
                arguments=message.function_call.arguments
            )

        usage = None
        if hasattr(response, "usage"):
            usage = {
                "completion_tokens": response.usage.completion_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            }

        return CompletionResponse(
            content=message.content,
            function_call=function_call,
            finish_reason=choice.finish_reason,
            usage=usage,
            cache_hit=getattr(response, "cache_hit", None)
        )

    async def close(self):
        """Close the client."""
        await self.client.close() 