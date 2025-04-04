"""
Example demonstrating how to use the LiteLLM client with Dewey and Aider configuration.

This script shows how the LiteLLMClient automatically loads configuration from:
1. Dewey config file (via symlink)
2. Aider model metadata (if available)
3. Environment variables (as fallback)
"""

import logging
import os
from pathlib import Path

from dewey.llm import (
    LiteLLMClient,
    create_message,
    get_available_models,
    get_text_from_response,
)
from dewey.llm.litellm_utils import (
    load_api_keys_from_aider,
    load_model_metadata_from_aider,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print a section title with separators."""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "-"))
    print("=" * 50 + "\n")


def check_config_paths():
    """Check and display the status of configuration files."""
    print_section("Configuration Paths")

    dewey_config = Path("/Users/srvo/dewey/config/dewey.yaml")
    llm_config = Path("/Users/srvo/dewey/src/dewey/llm/config.yaml")
    aider_conf = Path(os.path.expanduser("~/.aider.conf.yml"))
    aider_metadata = Path(os.path.expanduser("~/.aider.model.metadata.json"))

    print(f"Dewey config: {dewey_config.exists()}")
    print(f"LLM config symlink: {llm_config.exists()}")
    print(f"Aider config: {aider_conf.exists()}")
    print(f"Aider model metadata: {aider_metadata.exists()}")

    # Check if config.yaml is a symlink
    if llm_config.exists():
        if llm_config.is_symlink():
            target = llm_config.resolve()
            print(f"Symlink target: {target}")
        else:
            print("Warning: config.yaml exists but is not a symlink")


def show_aider_configuration():
    """Display Aider configuration details."""
    print_section("Aider Configuration")

    # Get API keys from Aider
    api_keys = load_api_keys_from_aider()
    if api_keys:
        print(f"Found {len(api_keys)} API keys in Aider config:")
        for provider in api_keys:
            print(f"  - {provider}: {'*' * 8}")
    else:
        print("No API keys found in Aider config")

    # Get model metadata from Aider
    model_metadata = load_model_metadata_from_aider()
    if model_metadata:
        print(f"\nFound {len(model_metadata)} models in Aider metadata:")
        for name, data in model_metadata.items():
            provider = data.get("litellm_provider", "unknown")
            max_tokens = data.get("max_tokens", "unknown")
            print(f"  - {name} (provider: {provider}, max tokens: {max_tokens})")
    else:
        print("No model metadata found in Aider config")


def create_client_and_test():
    """Create a LiteLLM client and test a simple completion."""
    print_section("LiteLLM Client Test")

    # Create the client (will auto-load from available configs)
    client = LiteLLMClient(verbose=True)

    # Print client configuration
    print(f"Model: {client.config.model}")
    print(f"Fallback models: {client.config.fallback_models}")
    print(f"Provider: {client.config.litellm_provider}")

    # List available models
    try:
        models = get_available_models()
        print(f"\nAvailable models: {len(models)}")
        for i, model in enumerate(models[:5]):  # Show first 5 models
            print(f"  {i + 1}. {model['id']}")
        if len(models) > 5:
            print(f"  ... and {len(models) - 5} more")
    except Exception as e:
        print(f"Error listing models: {e}")

    # Try a simple completion
    try:
        print("\nTesting completion...")
        messages = [
            create_message("system", "You are a helpful assistant."),
            create_message("user", "What is the capital of France?"),
        ]

        response = client.generate_completion(
            messages=messages, temperature=0.7, max_tokens=100,
        )

        text = get_text_from_response(response)
        print(f"\nResponse: {text}")

        # Print usage information
        if "usage" in response:
            usage = response["usage"]
            print("\nUsage:")
            print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")
    except Exception as e:
        print(f"Error during completion: {e}")


def main():
    """Main function to run the example."""
    print("LiteLLM Configuration Example")
    print("-----------------------------")

    check_config_paths()
    show_aider_configuration()
    create_client_and_test()

    print("\nExample completed.")


if __name__ == "__main__":
    main()
