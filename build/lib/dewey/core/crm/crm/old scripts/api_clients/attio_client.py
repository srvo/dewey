"""Client for interacting with Attio CRM API with dynamic schema handling."""
import json
import os
import requests
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
from api_docs_manager import load_docs

class AttioAPIError(Exception):
    """Base exception for Attio API interactions."""

class AttioClient:
    def __init__(self):
        self.api_key = os.getenv("ATTIO_API_KEY")
        self.logger = logging.getLogger(__name__)
        self.base_url = self._get_api_endpoint("Attio API")
        self.schema_version = self._get_schema_version()

    def _get_api_endpoint(self, api_name: str) -> str:
        """Get API base URL from documentation references"""
        api_docs = load_docs()
        doc_url = api_docs.get(api_name, "")

        # Use direct API domain instead of docs URL
        if "attio" in api_name.lower():
            return "https://api.attio.com"

        if not doc_url:
            raise AttioAPIError(
                f"Missing API documentation reference for {api_name}. "
                f"Use 'python api_docs_manager.py add \"{api_name}\" \"URL\"' to add it."
            )
            
        parsed = urlparse(doc_url)
        if not parsed.scheme or not parsed.netloc:
            raise AttioAPIError(
                f"Invalid URL format for {api_name} documentation: {doc_url}. "
                "Expected format: https://api.example.com/docs"
            )
            
        return f"{parsed.scheme}://{parsed.hostname}"

    def _get_schema_version(self) -> str:
        """Get current schema version for validation"""
        schema = self._get_contact_schema()
        return schema.get("version", "unknown")
        
    def _get_contact_schema(self) -> Dict:
        """Fetch schema with better error handling"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/objects/people",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            response.raise_for_status()
            schema = response.json()['data']
            
            if not schema.get('attributes'):
                raise AttioAPIError("Schema missing required 'attributes' field")
                
            return schema
        except KeyError as e:
            self.logger.error("Schema response missing 'data' key")
            raise AttioAPIError("Invalid schema response format") from e

    def get_contacts(self, batch_size: int = 100) -> List[Dict]:
        """Fetch contacts using the query endpoint"""
        return self._paginated_fetch("/v2/objects/people/records/query", {}, batch_size)

    def _paginated_fetch(self, endpoint: str, schema: Dict, batch_size: int) -> List[Dict]:
        """Handle pagination for any API endpoint using POST method."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json={},
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data:
                raise AttioAPIError(f"API response missing 'data' key: {data}")
                
            return data['data']
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"API request failed (HTTP {e.response.status_code}): {e.response.text}"
            self.logger.error(error_msg)
            raise AttioAPIError(error_msg) from e
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            self.logger.error(error_msg)
            raise AttioAPIError(error_msg) from e
