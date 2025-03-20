"""Tests for research utilities."""
import pytest
from unittest.mock import Mock, patch
import json
from pathlib import Path
from dewey.core.research.utils.universe_breakdown import UniverseBreakdown
from dewey.core.research.utils.sts_xml_parser import STSXMLParser
from dewey.core.research.utils.research_output_handler import ResearchOutputHandler
import logging
from dewey.core.base_script import BaseScript
from typing import Dict, Any, List

class TestUniverseBreakdown(BaseScript):
    """Test suite for universe breakdown utility."""

    def __init__(self):
        """Initializes the TestUniverseBreakdown class."""
        super().__init__(config_section='crm')

    def run(self):
        """Runs all tests for the UniverseBreakdown utility."""
        self.test_initialization(self.breakdown())
        self.test_analyze_universe(self.breakdown())
        self.test_generate_report(self.breakdown())

    @pytest.fixture
    def breakdown(self) -> UniverseBreakdown:
        """Create a test breakdown instance."""
        return UniverseBreakdown()

    def test_initialization(self, breakdown: UniverseBreakdown) -> None:
        """Test breakdown initialization.

        Args:
            breakdown: An instance of UniverseBreakdown.
        """
        assert breakdown is not None
        assert hasattr(breakdown, 'analyze')
        assert hasattr(breakdown, 'generate_report')

    def test_analyze_universe(self, breakdown: UniverseBreakdown) -> None:
        """Test universe analysis.

        Args:
            breakdown: An instance of UniverseBreakdown.
        """
        test_data: Dict[str, Any] = {
            "companies": [
                {"name": "Company A", "sector": "Technology", "market_cap": 1000000},
                {"name": "Company B", "sector": "Healthcare", "market_cap": 2000000},
                {"name": "Company C", "sector": "Technology", "market_cap": 1500000}
            ]
        }

        analysis: Dict[str, Any] = breakdown.analyze(test_data)
        assert isinstance(analysis, dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        assert analysis["sector_breakdown"]["Technology"] == 2
        assert analysis["sector_breakdown"]["Healthcare"] == 1

    def test_generate_report(self, breakdown: UniverseBreakdown) -> None:
        """Test report generation.

        Args:
            breakdown: An instance of UniverseBreakdown.
        """
        analysis_data: Dict[str, Any] = {
            "sector_breakdown": {"Technology": 2, "Healthcare": 1},
            "market_cap_distribution": {"large": 1, "medium": 2}
        }

        report: Dict[str, Any] = breakdown.generate_report(analysis_data)
        assert isinstance(report, dict)
        assert "summary" in report
        assert "charts" in report
        assert isinstance(report["charts"], list)

class TestSTSXMLParser(BaseScript):
    """Test suite for STS XML parser."""

    def __init__(self):
        """Initializes the TestSTSXMLParser class."""
        super().__init__(config_section='crm')

    def run(self):
        """Runs all tests for the STSXMLParser utility."""
        self.test_initialization(self.parser())
        self.test_parse_xml(self.parser())
        self.test_error_handling(self.parser())

    @pytest.fixture
    def parser(self) -> STSXMLParser:
        """Create a test parser instance."""
        return STSXMLParser()

    def test_initialization(self, parser: STSXMLParser) -> None:
        """Test parser initialization.

        Args:
            parser: An instance of STSXMLParser.
        """
        assert parser is not None
        assert hasattr(parser, 'parse')

    def test_parse_xml(self, parser: STSXMLParser) -> None:
        """Test XML parsing.

        Args:
            parser: An instance of STSXMLParser.
        """
        test_xml: str = """
        <sts-analysis>
            <company>
                <name>Test Corp</name>
                <metrics>
                    <metric name="revenue">1000000</metric>
                    <metric name="profit">200000</metric>
                </metrics>
            </company>
        </sts-analysis>
        """

        result: Dict[str, Any] = parser.parse(test_xml)
        assert isinstance(result, dict)
        assert "company" in result
        assert result["company"]["name"] == "Test Corp"
        assert result["company"]["metrics"]["revenue"] == "1000000"

    def test_error_handling(self, parser: STSXMLParser) -> None:
        """Test error handling in parsing.

        Args:
            parser: An instance of STSXMLParser.
        """
        with pytest.raises(ValueError):
            parser.parse("<invalid>xml</invalid>")

class TestResearchOutputHandler(BaseScript):
    """Test suite for research output handler."""

    def __init__(self):
        """Initializes the TestResearchOutputHandler class."""
        super().__init__(config_section='crm')

    def run(self):
        """Runs all tests for the ResearchOutputHandler utility."""
        self.test_initialization(self.handler())
        self.test_save_output(self.handler(), self.tmp_path())
        self.test_load_output(self.handler(), self.tmp_path())
        self.test_error_handling(self.handler())

    @pytest.fixture
    def handler(self) -> ResearchOutputHandler:
        """Create a test output handler instance."""
        return ResearchOutputHandler()

    @pytest.fixture
    def tmp_path(self, tmp_path: Path) -> Path:
        """Create a temporary path for testing."""
        return tmp_path

    def test_initialization(self, handler: ResearchOutputHandler) -> None:
        """Test handler initialization.

        Args:
            handler: An instance of ResearchOutputHandler.
        """
        assert handler is not None
        assert hasattr(handler, 'save')
        assert hasattr(handler, 'load')

    def test_save_output(self, handler: ResearchOutputHandler, tmp_path: Path) -> None:
        """Test saving research output.

        Args:
            handler: An instance of ResearchOutputHandler.
            tmp_path: A temporary directory path.
        """
        test_data: Dict[str, Any] = {
            "analysis": {
                "score": 85,
                "recommendations": ["Test recommendation"]
            },
            "timestamp": "2024-03-19T12:00:00"
        }

        output_path: Path = tmp_path / "test_output.json"
        handler.save(test_data, output_path)
        assert output_path.exists()

        # Verify saved content
        with open(output_path) as f:
            saved_data: Dict[str, Any] = json.load(f)
        assert saved_data == test_data

    def test_load_output(self, handler: ResearchOutputHandler, tmp_path: Path) -> None:
        """Test loading research output.

        Args:
            handler: An instance of ResearchOutputHandler.
            tmp_path: A temporary directory path.
        """
        test_data: Dict[str, Any] = {
            "analysis": {
                "score": 85,
                "recommendations": ["Test recommendation"]
            }
        }

        # Save test data
        output_path: Path = tmp_path / "test_output.json"
        with open(output_path, 'w') as f:
            json.dump(test_data, f)

        # Load and verify
        loaded_data: Dict[str, Any] = handler.load(output_path)
        assert loaded_data == test_data

    def test_error_handling(self, handler: ResearchOutputHandler) -> None:
        """Test error handling in output operations.

        Args:
            handler: An instance of ResearchOutputHandler.
        """
        with pytest.raises(FileNotFoundError):
            handler.load(Path("nonexistent.json"))

@pytest.mark.integration
class TestUtilsIntegration(BaseScript):
    """Integration tests for research utilities."""

    def __init__(self):
        """Initializes the TestUtilsIntegration class."""
        super().__init__(config_section='crm')

    def run(self, tmp_path: Path):
        """Runs the complete analysis workflow integration test.

        Args:
            tmp_path: A temporary directory path.
        """
        # Create test instances
        breakdown: UniverseBreakdown = UniverseBreakdown()
        parser: STSXMLParser = STSXMLParser()
        handler: ResearchOutputHandler = ResearchOutputHandler()

        # Test data
        test_xml: str = """
        <sts-analysis>
            <companies>
                <company>
                    <name>Tech Corp</name>
                    <sector>Technology</sector>
                    <market_cap>1000000</market_cap>
                </company>
                <company>
                    <name>Health Corp</name>
                    <sector>Healthcare</sector>
                    <market_cap>2000000</market_cap>
                </company>
            </companies>
        </sts-analysis>
        """

        # Parse XML
        parsed_data: Dict[str, Any] = parser.parse(test_xml)
        assert isinstance(parsed_data, dict)

        # Analyze universe
        analysis: Dict[str, Any] = breakdown.analyze(parsed_data)
        assert isinstance(analysis, dict)

        # Generate report
        report: Dict[str, Any] = breakdown.generate_report(analysis)
        assert isinstance(report, dict)

        # Save output
        output_path: Path = tmp_path / "analysis_output.json"
        handler.save(report, output_path)
        assert output_path.exists()

        # Load and verify output
        loaded_report: Dict[str, Any] = handler.load(output_path)
        assert loaded_report == report
