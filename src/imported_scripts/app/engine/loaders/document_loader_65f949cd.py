import logging
from typing import Any

import yaml  # type: ignore
from app.engine.loaders.db import DBLoaderConfig, get_db_documents
from app.engine.loaders.file import FileLoaderConfig, get_file_documents
from app.engine.loaders.web import WebLoaderConfig, get_web_documents
from llama_index.core import Document

logger = logging.getLogger(__name__)


def load_configs() -> dict[str, Any]:
    with open("config/loaders.yaml") as f:
        return yaml.safe_load(f)


def get_documents() -> list[Document]:
    documents = []
    config = load_configs()
    for loader_type, loader_config in config.items():
        logger.info(
            f"Loading documents from loader: {loader_type}, config: {loader_config}",
        )
        match loader_type:
            case "file":
                document = get_file_documents(FileLoaderConfig(**loader_config))
            case "web":
                document = get_web_documents(WebLoaderConfig(**loader_config))
            case "db":
                document = get_db_documents(
                    configs=[DBLoaderConfig(**cfg) for cfg in loader_config],
                )
            case _:
                msg = f"Invalid loader type: {loader_type}"
                raise ValueError(msg)
        documents.extend(document)

    return documents
