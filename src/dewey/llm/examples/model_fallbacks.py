#!/usr/bin/env python3
"""
Example of using model fallbacks with the LiteLLM client.

This script demonstrates how to configure model fallbacks to improve
reliability in case a primary model is unavailable or fails.
"""

import logging
import os

from dewey.llm import LiteLLMClient, LiteLLMConfig, Message, create_message

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the model fallbacks example."""
    # Set your API key (or load from environment)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return

    # Define primary model and fallbacks
    primary_model = "gpt-4"  # This could be any model, including one that might fail
    fallback_models = ["gpt-3.5-turbo", "claude-instant-1"]

    # Create a client configuration
    config = LiteLLMConfig(
        model=primary_model,
        api_key=api_key,
        temperature=0.7,
        max_tokens=150,
        fallback_models=fallback_models,
    )

    # Initialize the client
    client = LiteLLMClient(config)
    logger.info(f"Initialized LiteLLM client with model: {config.model}")
    logger.info(f"Fallback chain: {primary_model} → {' → '.join(fallback_models)}")

    # Create message objects
    system_message = create_message(
        "system", "You are a helpful assistant that provides concise answers.",
    )

    user_message = create_message(
        "user",
        "Explain the concept of model fallbacks in an AI system and why they're important.",
    )

    # Create a list of messages for the conversation
    messages: list[Message] = [system_message, user_message]

    # Generate a completion with fallbacks
    try:
        result = client.completion(messages)

        # Print the result
        print("\n--- Completion Result with Fallbacks ---")
        print(f"Model used: {result.model}")
        print(f"Response: {result.response_text}")
        print(
            f"Tokens used: {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})",
        )
        print(f"Response time: {result.response_ms}ms")

        # Check if a fallback was used
        if result.model != primary_model:
            print(
                f"\nFallback was used! Primary model '{primary_model}' failed, fell back to '{result.model}'",
            )

    except Exception as e:
        logger.error(f"Error generating completion with fallbacks: {e}")


if __name__ == "__main__":
    main()
