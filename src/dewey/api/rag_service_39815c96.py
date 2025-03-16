from fastapi import FastAPI
from lightrag import LightRAG

app = FastAPI()
rag = LightRAG()


@app.post("/query")
async def query(query: str):
    return {"response": rag.query(query)}


@app.get("/health")
async def health():
    return {"status": "healthy"}
