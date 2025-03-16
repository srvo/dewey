import os
import shutil
import tempfile
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from unstructured.partition.auto import partition

# Get configuration from environment variables
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

app = FastAPI(
    title="Unstructured Service",
    description="Service for extracting text from documents using unstructured-io",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/extract")
async def extract_text(file: Annotated[UploadFile, File()] = ...) -> dict:
    """Extract text from uploaded document."""
    try:
        # Create a temporary file to store the upload
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        try:
            # Process the document using unstructured
            elements = partition(temp_path)

            # Extract text from elements
            text_elements = []
            for element in elements:
                text_elements.append(
                    {
                        "type": element.__class__.__name__,
                        "text": str(element),
                        "metadata": element.metadata,
                    },
                )

            return {"filename": file.filename, "elements": text_elements}

        finally:
            # Clean up the temporary file
            os.unlink(temp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/supported-formats")
async def get_supported_formats() -> dict[str, list[str]]:
    """Get list of supported document formats."""
    return {
        "formats": ["pdf", "docx", "pptx", "xlsx", "txt", "json", "html", "eml", "msg"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL)
