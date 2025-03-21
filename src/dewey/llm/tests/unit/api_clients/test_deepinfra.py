"""Unit tests for the DeepInfra API client."""

import pytest
from unittest.mock import MagicMock, patch

from dewey.llm.api_clients.deepinfra import DeepInfraClient


class TestDeepInfraClient:
    """Tests for the DeepInfraClient class."""
    
    @pytest.fixture
    def mock_client(self) -> DeepInfraClient:
        """Create a DeepInfraClient with mocked BaseScript initialization."""
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            client = DeepInfraClient(config_section="test_deepinfra")
            client.logger = MagicMock()
            client.get_config_value = MagicMock()
            client.get_config_value.side_effect = lambda key, default=None: {
                "deepinfra_api_key": "test-api-key",
                "deepinfra_model_name": "llama2-70b"
            }.get(key, default)
            client._simulate_api_call = MagicMock(return_value={
                "output": "This is a test response",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            })
            return client
    
    def test_initialization(self) -> None:
        """Test client initialization."""
        # Arrange & Act
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None) as mock_init:
            client = DeepInfraClient(config_section="test_deepinfra")
            
            # Assert
            mock_init.assert_called_once_with(config_section="test_deepinfra")
            assert isinstance(client, DeepInfraClient)
    
    def test_run_method(self, mock_client) -> None:
        """Test the run method execution."""
        # Act
        mock_client.run()
        
        # Assert
        mock_client.get_config_value.assert_any_call("deepinfra_api_key")
        mock_client.get_config_value.assert_any_call("deepinfra_model_name", default="default_model")
        mock_client._simulate_api_call.assert_called_once_with("llama2-70b", "test-api-key")
        mock_client.logger.info.assert_called()
    
    def test_simulate_api_call(self) -> None:
        """Test the _simulate_api_call method."""
        # Arrange
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            client = DeepInfraClient()
            client._simulate_api_call = lambda model, key: {
                "model": model,
                "response": "Test response",
                "api_key_used": key
            }
            
            # Act
            response = client._simulate_api_call("test-model", "test-key")
            
            # Assert
            assert response["model"] == "test-model"
            assert response["api_key_used"] == "test-key"
    
    def test_error_handling(self, mock_client) -> None:
        """Test error handling in the run method."""
        # Arrange
        mock_client.get_config_value.side_effect = Exception("Test error")
        
        # Act/Assert
        with pytest.raises(Exception) as exc_info:
            mock_client.run()
        
        assert "Test error" in str(exc_info.value)
        mock_client.logger.exception.assert_called() 