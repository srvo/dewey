import asyncio

from scripts.enhanced_client import EnhancedSearchClient


async def main() -> None:
    client = EnhancedSearchClient(base_url="http://localhost:8000", api_key=None)

    try:
        await client.search(
            query="Hello, how are you?",
            model="gpt-4o",
            pro_search=False,
        )
    except Exception:
        pass
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
