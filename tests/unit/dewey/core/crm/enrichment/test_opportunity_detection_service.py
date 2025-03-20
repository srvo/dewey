import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.enrichment.opportunity_detection_service import (
    OpportunityDetectionService,
)


class TestOpportunityDetectionService:
    """Unit tests for the OpportunityDetectionService class."""

    @pytest.fixture
    def opportunity_detection_service(self) -> OpportunityDetectionService:
        """Fixture to create an instance of OpportunityDetectionService."""
        return OpportunityDetectionService()

    def test_init(self, opportunity_detection_service: OpportunityDetectionService) -> None:
        """Test the __init__ method."""
        assert opportunity_detection_service.config_section == "opportunity_detection"
        assert opportunity_detection_service.logger is not None
        assert isinstance(opportunity_detection_service.logger, logging.Logger)

    @patch("dewey.core.crm.enrichment.opportunity_detection_service.OpportunityDetectionService.detect_opportunities")
    def test_run(
        self,
        mock_detect_opportunities: MagicMock,
        opportunity_detection_service: OpportunityDetectionService,
    ) -> None:
        """Test the run method."""
        mock_detect_opportunities.return_value = ["demo"]
        opportunity_detection_service.logger = MagicMock()  # type: ignore
        opportunity_detection_service.run()
        mock_detect_opportunities.assert_called_once_with("This is a sample text with a demo opportunity.")
        opportunity_detection_service.logger.info.assert_called_once()  # type: ignore

    def test_detect_opportunities_no_patterns(
        self, opportunity_detection_service: OpportunityDetectionService
    ) -> None:
        """Test detect_opportunities when no regex patterns are configured."""
        opportunity_detection_service.get_config_value = MagicMock(return_value=None)  # type: ignore
        opportunities = opportunity_detection_service.detect_opportunities("test text")
        assert opportunities == []

    def test_detect_opportunities_empty_patterns(
        self, opportunity_detection_service: OpportunityDetectionService
    ) -> None:
        """Test detect_opportunities when regex patterns are empty."""
        opportunity_detection_service.get_config_value = MagicMock(return_value={})  # type: ignore
        opportunities = opportunity_detection_service.detect_opportunities("test text")
        assert opportunities == []

    def test_detect_opportunities_match(
        self, opportunity_detection_service: OpportunityDetectionService
    ) -> None:
        """Test detect_opportunities when a match is found."""
        opportunity_detection_service.get_config_value = MagicMock(  # type: ignore
            return_value={"demo": "demo"}
        )
        opportunity_detection_service._check_opportunity = MagicMock(return_value=True)  # type: ignore
        opportunities = opportunity_detection_service.detect_opportunities("test text with demo")
        assert opportunities == ["demo"]
        opportunity_detection_service._check_opportunity.assert_called_once_with(  # type: ignore
            "test text with demo", "demo"
        )

    def test_detect_opportunities_no_match(
        self, opportunity_detection_service: OpportunityDetectionService
    ) -> None:
        """Test detect_opportunities when no match is found."""
        opportunity_detection_service.get_config_value = MagicMock(  # type: ignore
            return_value={"demo": "demo"}
        )
        opportunity_detection_service._check_opportunity = MagicMock(return_value=False)  # type: ignore
        opportunities = opportunity_detection_service.detect_opportunities("test text")
        assert opportunities == []
        opportunity_detection_service._check_opportunity.assert_called_once_with(  # type: ignore
            "test text", "demo"
        )

    def test_detect_opportunities_multiple_patterns(
        self, opportunity_detection_service: OpportunityDetectionService
    ) -> None:
        """Test detect_opportunities with multiple regex patterns."""
        opportunity_detection_service.get_config_value = MagicMock(  # type: ignore
            return_value={"demo": "demo", "publicity": "publicity"}
        )
        opportunity_detection_service._check_opportunity = MagicMock(  # type: ignore
            side_effect=[True, False]
        )
        opportunities = opportunity_detection_service.detect_opportunities(
            "test text with demo and publicity"
        )
        assert opportunities == ["demo"]
        assert opportunity_detection_service._check_opportunity.call_count == 2  # type: ignore

    @pytest.mark.parametrize(
        "text, pattern, expected",
        [
            ("test text with demo", "demo", True),
            ("test text", "demo", False),
            ("DEMO", "demo", True),  # Case-insensitive
            ("test text with demo", r"\bdemo\b", True),  # Word boundary
            ("test text demoing", r"\bdemo\b", False),  # Word boundary
            ("", "demo", False),  # Empty text
            ("test text with demo", "", False),  # Empty pattern
        ],
    )
    def test_check_opportunity(
        self,
        opportunity_detection_service: OpportunityDetectionService,
        text: str,
        pattern: str,
        expected: bool,
    ) -> None:
        """Test _check_opportunity with various inputs."""
        result = opportunity_detection_service._check_opportunity(text, pattern)
        assert result == expected
