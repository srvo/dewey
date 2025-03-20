"""Tests for research utilities."""

import pytest
import json
from pathlib import Path
from dewey.core.research.utils.universe_breakdown import UniverseBreakdown
from dewey.core.research.utils.sts_xml_parser import STSXMLParser
from dewey.core.research.utils.research_output_handler import ResearchOutputHandler


class TestUniverseBreakdown:
    """Test suite for universe breakdown utility."""

    @pytest.fixture
    def breakdown(self):
        """Create a test breakdown instance."""
        return UniverseBreakdown()

    def test_initialization(self, breakdown):
        """Test breakdown initialization."""
        assert breakdown is not None
        assert hasattr(breakdown, "analyze")
        assert hasattr(breakdown, "generate_report")

    def test_analyze_universe(self, breakdown):
        """Test universe analysis."""
        test_data = {
            "companies": [
                {"name": "Company A", "sector": "Technology", "market_cap": 1000000},
                {"name": "Company B", "sector": "Healthcare", "market_cap": 2000000},
                {"name": "Company C", "sector": "Technology", "market_cap": 1500000},
            ]
        }

        analysis = breakdown.analyze(test_data)
        assert isinstance(analysis, dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        assert analysis["sector_breakdown"]["Technology"] == 2
        assert analysis["sector_breakdown"]["Healthcare"] == 1

    def test_generate_report(self, breakdown):
        """Test report generation."""
        analysis_data = {
            "sector_breakdown": {"Technology": 2, "Healthcare": 1},
            "market_cap_distribution": {"large": 1, "medium": 2},
        }

        report = breakdown.generate_report(analysis_data)
        assert isinstance(report, dict)
        assert "summary" in report
        assert "charts" in report
        assert isinstance(report["charts"], list)


class TestSTSXMLParser:
    """Test suite for STS XML parser."""

    @pytest.fixture
    def parser(self):
        """Create a test parser instance."""
        return STSXMLParser()

    def test_initialization(self, parser):
        """Test parser initialization."""
        assert parser is not None
        assert hasattr(parser, "parse")

    def test_parse_xml(self, parser):
        """Test XML parsing."""
        test_xml = """
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

        result = parser.parse(test_xml)
        assert isinstance(result, dict)
        assert "company" in result
        assert result["company"]["name"] == "Test Corp"
        assert result["company"]["metrics"]["revenue"] == "1000000"

    def test_error_handling(self, parser):
        """Test error handling in parsing."""
        with pytest.raises(ValueError):
            parser.parse("<invalid>xml</invalid>")


class TestResearchOutputHandler:
    """Test suite for research output handler."""

    @pytest.fixture
    def handler(self):
        """Create a test output handler instance."""
        return ResearchOutputHandler()

    def test_initialization(self, handler):
        """Test handler initialization."""
        assert handler is not None
        assert hasattr(handler, "save")
        assert hasattr(handler, "load")

    def test_save_output(self, handler, tmp_path):
        """Test saving research output."""
        test_data = {
            "analysis": {"score": 85, "recommendations": ["Test recommendation"]},
            "timestamp": "2024-03-19T12:00:00",
        }

        output_path = tmp_path / "test_output.json"
        handler.save(test_data, output_path)
        assert output_path.exists()

        # Verify saved content
        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data == test_data

    def test_load_output(self, handler, tmp_path):
        """Test loading research output."""
        test_data = {
            "analysis": {"score": 85, "recommendations": ["Test recommendation"]}
        }

        # Save test data
        output_path = tmp_path / "test_output.json"
        with open(output_path, "w") as f:
            json.dump(test_data, f)

        # Load and verify
        loaded_data = handler.load(output_path)
        assert loaded_data == test_data

    def test_error_handling(self, handler):
        """Test error handling in output operations."""
        with pytest.raises(FileNotFoundError):
            handler.load(Path("nonexistent.json"))


@pytest.mark.integration
class TestUtilsIntegration:
    """Integration tests for research utilities."""

    def test_complete_analysis_workflow(self, tmp_path):
        """Test complete analysis workflow using utilities."""
        # Create test instances
        breakdown = UniverseBreakdown()
        parser = STSXMLParser()
        handler = ResearchOutputHandler()

        # Test data
        test_xml = """
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
        parsed_data = parser.parse(test_xml)
        assert isinstance(parsed_data, dict)

        # Analyze universe
        analysis = breakdown.analyze(parsed_data)
        assert isinstance(analysis, dict)

        # Generate report
        report = breakdown.generate_report(analysis)
        assert isinstance(report, dict)

        # Save output
        output_path = tmp_path / "analysis_output.json"
        handler.save(report, output_path)
        assert output_path.exists()

        # Load and verify output
        loaded_report = handler.load(output_path)
        assert loaded_report == report
