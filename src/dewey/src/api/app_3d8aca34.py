from fastapi import FastAPI
from lightrag import LightRAG

app = FastAPI()
rag = LightRAG()


async def get_health_status() -> dict:
    """Returns the health status of the application.

    Returns
    -------
        dict: A dictionary containing the health status.

    """
    return {"status": "healthy"}


async def process_query(query: str) -> dict:
    """Processes a user query using LightRAG.

    Args:
    ----
        query: The user query string.

    Returns:
    -------
        dict: A dictionary containing the LightRAG response.

    """
    response = rag.query(query)
    return {"response": response}


@app.post("/query")
async def query(query: str):
    """Endpoint for processing user queries.

    Args:
    ----
        query (str): The user query.

    Returns:
    -------
        dict: A dictionary containing the LightRAG response.

    """
    return await process_query(query)


@app.get("/health")
async def health():
    """Endpoint for checking the health of the application.

    Returns
    -------
        dict: A dictionary containing the health status.

    """
    return await get_health_status()
