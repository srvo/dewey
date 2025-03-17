import asyncio
from search_client import SearchClient

async def main():
    client = SearchClient(
        base_url="http://your-farfalle-instance",
        api_key="your-api-key"  # Optional depending on your setup
    )
    
    try:
        results = await client.search("Python programming")
        print(results)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 