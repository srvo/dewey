from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from app.config import DATA_DIR
from pydantic import BaseModel

if TYPE_CHECKING:
    from llama_index.core.schema import NodeWithScore

logger = logging.getLogger("uvicorn")


class SourceNodes(BaseModel):
    id: str
    metadata: dict[str, Any]
    score: float | None
    text: str
    url: str | None

    @classmethod
    def from_source_node(cls, source_node: NodeWithScore):
        metadata = source_node.node.metadata
        url = cls.get_url_from_metadata(metadata)

        # Extract financial-specific metadata with enhanced data types
        financial_metadata = {
            "document_type": metadata.get("file_type"),
            "client_name": metadata.get("client_name"),
            "date": metadata.get("date"),
            "financial_year": (
                int(metadata.get("financial_year"))
                if metadata.get("financial_year")
                else None
            ),
            "currency": metadata.get("currency"),
            "total_assets": (
                float(metadata.get("total_assets"))
                if metadata.get("total_assets")
                else None
            ),
            "total_liabilities": (
                float(metadata.get("total_liabilities"))
                if metadata.get("total_liabilities")
                else None
            ),
            "net_worth": (
                float(metadata.get("net_worth")) if metadata.get("net_worth") else None
            ),
            "financial_ratios": {
                "debt_to_equity": None,
                "current_ratio": None,
                "return_on_equity": None,
            },
            "risk_indicators": {
                "liquidity_risk": None,
                "market_risk": None,
                "credit_risk": None,
            },
        }

        # Merge with existing metadata
        metadata.update({k: v for k, v in financial_metadata.items() if v is not None})

        return cls(
            id=source_node.node.node_id,
            metadata=metadata,
            score=source_node.score,
            text=source_node.node.text,  # type: ignore
            url=url,
        )

    @classmethod
    def get_url_from_metadata(cls, metadata: dict[str, Any]) -> str | None:
        url_prefix = os.getenv("FILESERVER_URL_PREFIX")
        if not url_prefix:
            logger.warning(
                "Warning: FILESERVER_URL_PREFIX not set in environment variables. Can't use file server",
            )
        file_name = metadata.get("file_name")

        if file_name and url_prefix:
            # file_name exists and file server is configured
            pipeline_id = metadata.get("pipeline_id")
            if pipeline_id:
                # file is from LlamaCloud
                file_name = f"{pipeline_id}${file_name}"
                return f"{url_prefix}/output/llamacloud/{file_name}"
            is_private = metadata.get("private", "false") == "true"
            if is_private:
                # file is a private upload
                return f"{url_prefix}/output/uploaded/{file_name}"
            # file is from calling the 'generate' script
            # Get the relative path of file_path to data_dir
            file_path = metadata.get("file_path")
            data_dir = os.path.abspath(DATA_DIR)
            if file_path and data_dir:
                relative_path = os.path.relpath(file_path, data_dir)
                return f"{url_prefix}/data/{relative_path}"
        # fallback to URL in metadata (e.g. for websites)
        return metadata.get("URL")

    @classmethod
    def from_source_nodes(cls, source_nodes: list[NodeWithScore]):
        return [cls.from_source_node(node) for node in source_nodes]
