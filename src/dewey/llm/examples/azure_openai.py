#!/usr/bin/env python3
"""
Example of using Azure OpenAI with the LiteLLM client.

This script demonstrates how to configure and use Azure OpenAI
through the LiteLLM client.
"""

import os
import logging
from typing import List

from dewey.llm import (
    LiteLLMClient,
    LiteLLMConfig,
    Message,
    configure_azure_openai,
    create_message,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the Azure OpenAI example."""
    # Get Azure OpenAI configuration from environment variables
    azure_api_key = os.environ.get("AZURE_API_KEY")
    azure_api_base = os.environ.get("AZURE_API_BASE")
    azure_api_version = os.environ.get("AZURE_API_VERSION", "2023-05-15")
    azure_deployment_name = os.environ.get("AZURE_DEPLOYMENT_NAME")

    # Check if Azure OpenAI configuration is set
    if not all([azure_api_key, azure_api_base, azure_deployment_name]):
        logger.error("Azure OpenAI configuration is not complete")
        logger.error(
            "Please set AZURE_API_KEY, AZURE_API_BASE, and AZURE_DEPLOYMENT_NAME environment variables"
        )
        return

    # Configure Azure OpenAI
    try:
        configure_azure_openai(
            api_key=azure_api_key,
            api_base=azure_api_base,
            api_version=azure_api_version,
            deployment_name=azure_deployment_name,
        )
        logger.info("Azure OpenAI configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Azure OpenAI: {e}")
        return

    # Create a client configuration for Azure OpenAI
    # Note: When using Azure, the model name should be in the format:
    # azure/<deployment_name>
    config = LiteLLMConfig(
        model=f"azure/{azure_deployment_name}",
        azure_api_base=azure_api_base,
        azure_api_version=azure_api_version,
        azure_deployment_name=azure_deployment_name,
        temperature=0.7,
        max_tokens=150,
    )

    # Initialize the client
    client = LiteLLMClient(config)
    logger.info(
        f"Initialized LiteLLM client for Azure OpenAI with model: {config.model}"
    )

    # Create message objects
    system_message = create_message(
        "system", "You are a helpful assistant that provides concise answers."
    )

    user_message = create_message(
        "user",
        "What are the advantages of using Azure OpenAI over direct OpenAI API access?",
    )

    # Create a list of messages for the conversation
    messages: List[Message] = [system_message, user_message]

    # Generate a completion
    try:
        result = client.completion(messages)

        # Print the result
        print("\n--- Azure OpenAI Completion Result ---")
        print(f"Model used: {result.model}")
        print(f"Response: {result.response_text}")
        print(
            f"Tokens used: {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})"
        )
        print(f"Response time: {result.response_ms}ms")

    except Exception as e:
        logger.error(f"Error generating completion with Azure OpenAI: {e}")


if __name__ == "__main__":
    main()
