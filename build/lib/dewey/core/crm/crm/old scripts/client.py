from typing import AsyncGenerator, Dict, List, Optional, Any
from .models import (
    CompletionRequest,
    CompletionResponse,
    ModelConfig,
    Message,
    Function,
    FIMRequest,
    UseCase,
    ModelProvider
)
from .providers import LLMProvider, DeepSeekProvider

class AIClient:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @classmethod
    def create(cls, provider: ModelProvider, api_key: str, **kwargs) -> 'AIClient':
        """Create an AI client with the specified provider."""
        if provider == ModelProvider.DEEPSEEK:
            return cls(DeepSeekProvider(api_key, **kwargs))
        raise ValueError(f"Unsupported provider: {provider}")

    async def complete(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        use_case: UseCase = UseCase.CHAT,
        functions: Optional[List[Function]] = None,
        cache_id: Optional[str] = None,
        **kwargs
    ) -> CompletionResponse:
        """Send a completion request."""
        config = ModelConfig(
            model_name=model,
            temperature=temperature,
            functions=functions,
            **kwargs
        )
        request = CompletionRequest(
            messages=messages,
            config=config,
            cache_id=cache_id
        )
        return await self.provider.complete(request)

    async def complete_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        use_case: UseCase = UseCase.CHAT,
        functions: Optional[List[Function]] = None,
        cache_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[CompletionResponse, None]:
        """Send a streaming completion request."""
        config = ModelConfig(
            model_name=model,
            temperature=temperature,
            functions=functions,
            **kwargs
        )
        request = CompletionRequest(
            messages=messages,
            config=config,
            cache_id=cache_id
        )
        async for response in self.provider.complete_stream(request):
            yield response

    async def fim_complete(
        self,
        prompt: str,
        suffix: str,
        max_tokens: int = 100
    ) -> CompletionResponse:
        """Send a fill-in-the-middle completion request."""
        request = FIMRequest(
            prompt=prompt,
            suffix=suffix,
            max_tokens=max_tokens
        )
        return await self.provider.fim_complete(request)

    async def close(self):
        """Close the client and its provider."""
        await self.provider.close() 