import asyncio

from farfalle import FarfalleClient


async def search_query():
    client = FarfalleClient(api_key="your_key")
    return await client.search("your query")


if __name__ == "__main__":
    asyncio.run(search_query())
