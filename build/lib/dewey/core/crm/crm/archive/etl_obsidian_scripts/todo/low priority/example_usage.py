import asyncio
from farfalle import FarfalleClient

async def search_query():
    client = FarfalleClient(api_key="your_key")
    response = await client.search("your query")
    return response

if __name__ == "__main__":
    asyncio.run(search_query()) 