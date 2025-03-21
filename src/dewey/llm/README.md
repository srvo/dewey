# LiteLLM Integration for Dewey

This module provides a seamless integration of the [LiteLLM](https://docs.litellm.ai/docs/) library into the Dewey framework, allowing for consistent interaction with various Large Language Model (LLM) providers through a unified API.

## Features

- **Unified API**: Interact with multiple LLM providers (OpenAI, Azure, Anthropic, etc.) using a consistent interface
- **Model Fallbacks**: Configure backup models to ensure reliability in case a primary model fails
- **Error Handling**: Robust error handling with custom exception types
- **Async Support**: Both synchronous and asynchronous API calls
- **Environment Integration**: Easy configuration through environment variables
- **Embeddings**: Generate and use embeddings alongside completions

## Usage

### Basic Completion

```python
from dewey.llm import LiteLLMClient, create_message

# Initialize client (uses environment variables by default)
client = LiteLLMClient()

# Create messages
system_msg = create_message("system", "You are a helpful assistant.")
user_msg = create_message("user", "What is the capital of France?")

# Generate completion
result = client.completion([system_msg, user_msg])
print(result.response_text)
```

### Configuration

```python
from dewey.llm import LiteLLMClient, LiteLLMConfig

# Create custom configuration
config = LiteLLMConfig(
    model="gpt-4",
    api_key="your-api-key",
    temperature=0.7,
    max_tokens=500,
    fallback_models=["gpt-3.5-turbo"]
)

# Initialize client with config
client = LiteLLMClient(config)
```

### Azure OpenAI

```python
from dewey.llm import configure_azure_openai, LiteLLMClient, LiteLLMConfig

# Configure Azure OpenAI
configure_azure_openai(
    api_key="your-azure-api-key",
    api_base="your-azure-endpoint",
    api_version="2023-05-15",
    deployment_name="your-deployment-name"
)

# Create client configuration
config = LiteLLMConfig(
    model="azure/your-deployment-name",
    azure_api_base="your-azure-endpoint",
    azure_api_version="2023-05-15",
    azure_deployment_name="your-deployment-name"
)

# Initialize client
client = LiteLLMClient(config)
```

## Examples

Check out the examples directory for more detailed usage:

- `basic_completion.py`: Simple text completion example
- `azure_openai.py`: Using Azure OpenAI integration
- `model_fallbacks.py`: Setting up model fallbacks for reliability

## Environment Variables

The module supports the following environment variables:

- `OPENAI_API_KEY`: OpenAI API key
- `AZURE_API_KEY`: Azure OpenAI API key
- `AZURE_API_BASE`: Azure OpenAI endpoint
- `AZURE_API_VERSION`: Azure OpenAI API version
- `AZURE_DEPLOYMENT_NAME`: Azure OpenAI deployment name
- `ANTHROPIC_API_KEY`: Anthropic API key
- `COHERE_API_KEY`: Cohere API key
- `HUGGINGFACE_API_KEY`: Hugging Face API key
- `MISTRAL_API_KEY`: Mistral API key
- `GOOGLE_API_KEY`: Google API key (for Palm/Gemini)
- `LITELLM_MODEL`: Default model to use
- `LITELLM_MAX_TOKENS`: Default max tokens to generate
- `LITELLM_TEMPERATURE`: Default temperature setting
- `LITELLM_TIMEOUT`: Default request timeout in seconds
- `LITELLM_MAX_RETRIES`: Default number of retries
- `LITELLM_VERBOSE`: Whether to enable verbose logging ("true"/"false")
- `LITELLM_FALLBACKS`: Comma-separated list of fallback models

## Error Handling

The module provides custom exceptions for handling different types of errors:

- `LLMConnectionError`: When there's an issue connecting to the provider
- `LLMResponseError`: When there's an issue with the response
- `LLMTimeoutError`: When the request times out
- `LLMRateLimitError`: When the rate limit is exceeded
- `LLMAuthenticationError`: When there's an issue with authentication
- `InvalidPromptError`: When the prompt is invalid

Example:

```python
from dewey.llm import LiteLLMClient, LLMAuthenticationError, LLMTimeoutError

client = LiteLLMClient()

try:
    result = client.completion(messages)
    print(result.response_text)
except LLMAuthenticationError as e:
    print(f"Authentication error: {e}")
except LLMTimeoutError as e:
    print(f"Request timed out: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

## Advanced Usage

### Asynchronous Completions

```python
import asyncio
from dewey.llm import LiteLLMClient, create_message

async def generate_async():
    client = LiteLLMClient()
    messages = [
        create_message("user", "What is the capital of France?")
    ]
    result = await client.acompletion(messages)
    return result.response_text

# Run the async function
response = asyncio.run(generate_async())
print(response)
```

### Embeddings

```python
from dewey.llm import LiteLLMClient

client = LiteLLMClient()

# Generate embeddings for a single text
text = "This is a sample text for embedding"
result = client.get_embeddings(text, model="text-embedding-ada-002")

# Or for multiple texts
texts = ["First text", "Second text", "Third text"]
results = client.get_embeddings(texts, model="text-embedding-ada-002")
``` 