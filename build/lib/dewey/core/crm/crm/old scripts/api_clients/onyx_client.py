"""Client for Onyx API with universal search capabilities."""
import os
import requests
import logging
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse
from api_docs_manager import load_docs

class OnyxAPIError(Exception):
    """Base exception for Onyx API interactions."""

class OnyxClient:
    def __init__(self):
        self.api_key = os.getenv("ONYX_API_KEY")
        self.logger = logging.getLogger(__name__)
        self.base_url = self._get_valid_base_url()

    def _get_valid_base_url(self) -> str:
        """Get and validate base URL from API docs with error handling"""
        api_docs = load_docs().get("links", {})
        doc_url = api_docs.get("Onyx_ingestion", "").strip()
        
        if not doc_url:
            raise OnyxAPIError(
                "Missing Onyx API documentation URL\n"
                "Fix with: python api_docs_manager.py add Onyx_ingestion <API_DOCS_URL>"
            )
            
        parsed = urlparse(doc_url)
        if not parsed.scheme or not parsed.netloc:
            raise OnyxAPIError(f"Invalid Onyx URL format: {doc_url}\nMust include http:// or https://")

        # Extract base domain without path
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def universal_search(self, contact: Dict) -> Dict:
        """Search across connected data sources with proper error handling."""
        try:
            query = self._build_search_query(contact)
            response = requests.post(
                f"{self.base_url}/ingestion/search",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=self._build_search_payload(query),
                timeout=20
            )
            response.raise_for_status()
            return self._format_response(response.json())
        except requests.exceptions.MissingSchema as e:
            self.logger.error("Invalid URL structure: %s", str(e))
            return self._error_response(e)
        except requests.exceptions.RequestException as e:
            self.logger.error("Search failed: %s", str(e))
            return self._error_response(e)

    def _build_search_query(self, contact: Dict) -> str:
        """Construct OR query from available contact fields."""
        return " OR ".join(
            f'"{v}"' for v in contact.values()
            if isinstance(v, str) and v.strip()
        )

    def _build_search_payload(self, query: str) -> Dict:
        """Construct API request body per documentation."""
        return {
            "query": {
                "type": "unified_search",
                "parameters": {
                    "q": query,
                    "sources": ["gmail", "google_docs"],
                    "max_results": 25,
                    "strict_validation": True
                }
            },
            "request_metadata": {
                "request_id": f"search_{datetime.utcnow().timestamp()}",
                "requested_at": datetime.utcnow().isoformat()
            }
        }

    def _format_response(self, raw: Dict) -> Dict:
        """Normalize API response structure."""
        return {
            "metadata": {
                "api_reference": load_docs().get("links", {}).get("Onyx_ingestion"),
                "timestamp": datetime.utcnow().isoformat(),
                "result_count": len(raw.get("data", []))
            },
            "results": [
                {
                    "source": item.get("source_type"),
                    "content": item.get("content"),
                    "confidence": item.get("confidence_score", 0),
                    "raw": item
                }
                for item in raw.get("data", [])
            ]
        }

    def _error_response(self, error: Exception) -> Dict:
        """Format error response consistently."""
        return {
            "metadata": {
                "error": str(error),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            },
            "results": []
        }
