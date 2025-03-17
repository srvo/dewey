import asyncio
from scripts.enhanced_client import EnhancedSearchClient

async def main():
    client = EnhancedSearchClient(
        base_url="http://localhost:8000",
        api_key=None
    )
    
    try:
        print("\nTesting API...")
        results = await client.search(
            query="Hello, how are you?",
            model="gpt-4o",
            pro_search=False
        )
        print(f"Results: {results}")
    except Exception as e:
        print(f"Search failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 