import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from unittest.mock import patch, MagicMock
import os
import logging
from datetime import datetime
import requests

from ..api_clients.onyx_client import OnyxClient

class TestOnyxClient(unittest.TestCase):
    def setUp(self):
        # Mock the API docs loading
        self.docs_patch = patch('api_docs_manager.load_docs')
        mock_load_docs = self.docs_patch.start()
        mock_load_docs.return_value = {
            "links": {
                "Onyx_ingestion": "https://api.onyx.example.com"
            }
        }
        
        self.api_key = "test_api_key"
        self.client = OnyxClient()

    def tearDown(self):
        self.docs_patch.stop()

    @patch.dict(os.environ, {"ONYX_API_KEY": "test_api_key"})
    def test_init(self):
        with patch('api_docs_manager.load_docs') as mock_load_docs:
            mock_load_docs.return_value = {
                "links": {
                    "Onyx_ingestion": "https://api.onyx.example.com"
                }
            }
            client = OnyxClient()
            self.assertEqual(client.api_key, self.api_key)

    @patch("requests.post")
    def test_universal_search_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "confidence": 0.8}
        mock_post.return_value = mock_response
        response = self.client.universal_search({"name": "John Doe", "email": "john@example.com"})
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["confidence"], 0.8)

    @patch("requests.post")
    def test_universal_search_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_post.return_value = mock_response
        
        response = self.client.universal_search({"name": "John Doe"})
        self.assertEqual(response["metadata"]["status"], "error")
        self.assertIn("403", response["metadata"]["error"])

    def test_build_search_query(self):
        contact_data = {"name": "John Doe", "email": "john@example.com", "company": "Example Inc."}
        query = self.client._build_search_query(contact_data)
        self.assertIn(contact_data["name"], query)
        self.assertIn(contact_data["email"], query)
        self.assertIn(contact_data["company"], query)

    def test_build_search_payload(self):
        query = "test query"
        payload = self.client._build_search_payload(query)
        
        # Test actual structure from onyx_client.py
        self.assertEqual(payload["query"]["type"], "unified_search")
        self.assertEqual(payload["query"]["parameters"]["q"], query)
        self.assertEqual(payload["query"]["parameters"]["sources"], ["gmail", "google_docs"])
        self.assertEqual(payload["query"]["parameters"]["max_results"], 25)
        self.assertEqual(payload["query"]["parameters"]["strict_validation"], True)

    def test_format_response(self):
        raw_response = {
            "data": [
                {
                    "source_type": "gmail",
                    "content": "test content",
                    "confidence_score": 0.8,
                    "id": "123"
                }
            ]
        }
        response = self.client._format_response(raw_response)
        
        self.assertEqual(response["metadata"]["result_count"], 1)
        self.assertEqual(response["results"][0]["confidence"], 0.8)
        self.assertEqual(response["results"][0]["source"], "gmail")

    @patch("requests.post")
    def test_network_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Network error")
        response = self.client.universal_search({"name": "John Doe", "email": "john@example.com"})
        self.assertEqual(response["status"], "error")
        self.assertIn("Network error", response["message"])

    def test_error_response(self):
        error_message = "Test error message"
        response = self.client._error_response(error_message)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], error_message)
        self.assertIsInstance(response["timestamp"], str)

class LiveOnyxClientTests(unittest.TestCase):
    """ACTUAL API CALL TESTS (requires valid ONYX_API_KEY)"""
    
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv()
        
        cls.api_key = os.getenv("ONYX_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("ONYX_API_KEY not found - skipping live tests")
            
        cls.client = OnyxClient()
        cls.valid_contact = {
            "name": "John Doe",
            "email": "john@example.com",
            "company": "Test Corp",
            "phone": "+1-555-123-4567"
        }
    
    def test_real_api_response_structure(self):
        """Should get valid response structure from live API"""
        response = self.client.universal_search(self.valid_contact)
        
        self.assertIn("metadata", response)
        self.assertIn("results", response)
        
        if response["metadata"].get("error"):
            self.fail(f"API Error: {response['metadata']['error']}")
        else:
            self.assertGreater(len(response["results"]), 0)
            for result in response["results"]:
                self.assertIn("source", result)
                self.assertIn("content", result)

    def test_invalid_credentials_handling(self):
        """Should handle invalid API keys properly"""
        invalid_client = OnyxClient()
        invalid_client.api_key = "invalid_key"
        
        with self.assertRaises(Exception) as context:
            invalid_client.universal_search(self.valid_contact)
            
        self.assertIn("401", str(context.exception))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
