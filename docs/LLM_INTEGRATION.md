# LLM Integration Guide

## DeepInfra Implementation

Uses OpenAI-compatible API with these key configurations:

```python
from dewey.llm.llm_utils import generate_response

response = generate_response(
    prompt="What's the capital of France?",
    system_message="You are a helpful assistant"
)
```

## Environment Configuration
Set these in your `.env` file:
```ini
DEEPINFRA_API_KEY=your-key-here
```

## Error Handling
Catch `LLMError` for any API-related exceptions
