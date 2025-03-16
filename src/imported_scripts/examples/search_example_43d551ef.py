import asyncio

from search_client import SearchClient


async def main() -> None:
    client = SearchClient(
        base_url="http://your-farfalle-instance",
        api_key="your-api-key",  # Optional depending on your setup
    )

    try:
        await client.search("Python programming")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
