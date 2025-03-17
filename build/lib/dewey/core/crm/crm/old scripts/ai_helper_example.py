import asyncio
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from ai_helper.models import Message, UseCase, ModelProvider, CompletionResponse
from ai_helper.client import AIClient

async def code_analysis_example(client: AIClient) -> CompletionResponse:
    """Example of code analysis capability."""
    code = '''
    def process_data(data):
        results = []
        for item in data:
            if isinstance(item, dict):
                results.append(item.get('value', 0))
            elif isinstance(item, (int, float)):
                results.append(item)
        return sum(results)
    '''
    
    messages = [
        Message(role="user", content=f"Analyze this code for potential improvements and edge cases:\n{code}")
    ]
    return await client.complete(
        messages=messages,
        model="deepseek-chat",
        use_case=UseCase.CODE_ANALYSIS
    )

async def multi_step_reasoning(client: AIClient) -> CompletionResponse:
    """Example of multi-step reasoning process."""
    messages = [
        Message(role="user", content="Let's solve this step by step: A company's revenue grew by 15% in 2021 and 25% in 2022. If their revenue in 2020 was $1M, what was their revenue in 2022?")
    ]
    return await client.complete(
        messages=messages,
        model="deepseek-chat",
        use_case=UseCase.ANALYSIS
    )

async def function_calling_example(client: AIClient) -> Dict[str, Any]:
    """Example of function calling capability."""
    def extract_data_points(text: str) -> Dict[str, Any]:
        """Extract numerical data points from text."""
        return {"extracted": True, "text": text}

    messages = [
        Message(role="user", content="The temperature today is 72°F with 45% humidity.")
    ]
    
    response = await client.complete(
        messages=messages,
        model="deepseek-chat",
        use_case=UseCase.FUNCTION_CALLING,
        functions=[{
            "name": "extract_data_points",
            "description": "Extract numerical values from text",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "number"},
                    "humidity": {"type": "number"}
                }
            }
        }]
    )
    
    return response.function_call

async def error_handling_example(client: AIClient) -> CompletionResponse:
    """Example of error handling and retries."""
    try:
        messages = [
            Message(role="user", content="Generate a very long response that might hit token limits")
        ]
        return await client.complete(
            messages=messages,
            model="deepseek-chat",
            use_case=UseCase.CHAT,
            max_retries=3
        )
    except Exception as e:
        print(f"Error handled: {str(e)}")
        messages = [
            Message(role="user", content="Please provide a shorter response")
        ]
        return await client.complete(
            messages=messages,
            model="deepseek-chat",
            use_case=UseCase.CHAT
        )

async def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")

    # Create AI client
    client = AIClient.create(
        provider=ModelProvider.DEEPSEEK,
        api_key=api_key
    )

    try:
        # Example 1: Code Analysis
        print("\nCode Analysis Example:")
        response = await code_analysis_example(client)
        print(response.content)

        # Example 2: Multi-step Reasoning
        print("\nMulti-step Reasoning Example:")
        response = await multi_step_reasoning(client)
        print(response.content)

        # Example 3: Function Calling
        print("\nFunction Calling Example:")
        result = await function_calling_example(client)
        print(result)

        # Example 4: Error Handling
        print("\nError Handling Example:")
        response = await error_handling_example(client)
        print(response.content)

        # Example 5: Fill-in-the-middle completion
        print("\nFill-in-the-middle Example:")
        response = await client.fim_complete(
            prompt="def calculate_sum(a, b):",
            suffix="return result"
        )
        print(response.content)

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 