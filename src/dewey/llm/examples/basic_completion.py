#!/usr/bin/env python3
"""
Basic example of using the LiteLLM client for text completion.

This script demonstrates how to initialize the LiteLLM client and
generate a simple text completion.
"""

import os
import logging
from typing import List

from dewey.llm import (
    LiteLLMClient,
    LiteLLMConfig,
    Message,
    create_message,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the basic completion example."""
    # Set your API key (or load from environment)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return

    # Create a client configuration
    config = LiteLLMConfig(
        model="gpt-3.5-turbo",
        api_key=api_key,
        temperature=0.7,
        max_tokens=150,
    )

    # Initialize the client
    client = LiteLLMClient(config)
    logger.info(f"Initialized LiteLLM client with model: {config.model}")

    # Create message objects
    system_message = create_message(
        "system", "You are a helpful assistant that provides concise answers."
    )

    user_message = create_message(
        "user",
        "What are the key features of Python that make it popular for data science?",
    )

    # Create a list of messages for the conversation
    messages: List[Message] = [system_message, user_message]

    # Generate a completion
    try:
        result = client.completion(messages)

        # Print the result
        print("\n--- Completion Result ---")
        print(f"Model used: {result.model}")
        print(f"Response: {result.response_text}")
        print(
            f"Tokens used: {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})"
        )
        print(f"Response time: {result.response_ms}ms")

    except Exception as e:
        logger.error(f"Error generating completion: {e}")


if __name__ == "__main__":
    main()
