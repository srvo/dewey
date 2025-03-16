```python
"""Tests for database data processing and conversion."""

from datetime import datetime
from typing import Any, Dict

import pytest

from ethifinx.db.converters import database_to_workflow, workflow_to_database
from ethifinx.db.data_processing import DataProcessor


@pytest.fixture
def sample_workflow_data() -> Dict[str, Any]:
    """Sample workflow output data."""
    return {
        "analysis_id": "test_analysis",
        "timestamp": datetime.now().isoformat(),
        "tags": {
            "concern_level": 3,
            "opportunity_score": 4,
            "interest_level": 3,
            "source_reliability": 4,
            "key_concerns": ["Environmental impact", "Labor practices"],
            "key_opportunities": ["Green initiatives", "Worker training"],
            "confidence_score": 0.85,
            "primary_themes": ["sustainability", "workforce"],
        },
        "summary": {
            "key_findings": "Company shows mixed performance",
            "main_risks": "Environmental concerns\nLabor issues",
            "main_opportunities": "Green programs\nTraining initiatives",
            "recommendation": "Monitor closely",
            "next_steps": "Investigate environmental practices",
        },
        "metadata": {
            "text_length": 1000,
            "context_used": True,
            "processing_version": "1.0",
        },
    }


@pytest.fixture
def sample_research_data() -> Dict[str, Any]:
    """Sample research data."""
    return {
        "content": "Research findings about company X",
        "source": "Annual Report 2023",
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_database_data() -> Dict[str, Any]:
    """Sample database format data."""
    return {
        "id": 123,
        "structured_data": {
            "concern_level": 3,
            "opportunity_score": 4,
            "interest_level": 3,
            "source_reliability": 4,
            "key_concerns": ["Environmental impact", "Labor practices"],
            "key_opportunities": ["Green initiatives", "Worker training"],
            "confidence_score": 85,
            "primary_themes": ["sustainability", "workforce"],
        },
        "summary": "Company shows mixed performance",
        "recommendation": "Monitor closely",
        "last_updated_at": datetime.now(),
    }


def test_data_processor_workflow_data(sample_workflow_data: Dict[str, Any]) -> None:
    """Test processing of workflow data."""
    processor = DataProcessor()
    result = processor.process(sample_workflow_data)

    assert "structured_data" in result
    assert "raw_results" in result
    assert "summary" in result
    assert "risk_score" in result
    assert "confidence_score" in result
    assert isinstance(result["confidence_score"], int)
    assert 0 <= result["confidence_score"] <= 100


def test_data_processor_research_data(sample_research_data: Dict[str, Any]) -> None:
    """Test processing of research data."""
    processor = DataProcessor()
    result = processor.process(sample_research_data)

    assert result["content"] == sample_research_data["content"]
    assert result["source"] == sample_research_data["source"]
    assert "timestamp" in result
    assert "metadata" in result
    assert result["metadata"]["original_format"] == "research_data"


def test_data_processor_invalid_data() -> None:
    """Test processing of invalid data."""
    processor = DataProcessor()

    # Test None input
    with pytest.raises(ValueError, match="Data cannot be None"):
        processor.process(None)

    # Test non-dict input
    with pytest.raises(ValueError, match="Data must be a dictionary"):
        processor.process([])

    # Test empty dict
    with pytest.raises(ValueError, match="Data dictionary cannot be empty"):
        processor.process({})

    # Test dict with None values
    with pytest.raises(TypeError, match="Data values cannot be None"):
        processor.process({"key": None})


def test_workflow_to_database_conversion(sample_workflow_data: Dict[str, Any]) -> None:
    """Test conversion from workflow to database format."""
    result = workflow_to_database(sample_workflow_data)

    assert isinstance(result["structured_data"], dict)
    assert isinstance(result["confidence_score"], int)
    assert 0 <= result["confidence_score"] <= 100
    assert "history" not in result["structured_data"]


def test_workflow_to_database_with_history(sample_workflow_data: Dict[str, Any]) -> None:
    """Test conversion with existing data merging."""
    existing_data: Dict[str, Any] = {
        "structured_data": {
            "concern_level": 2,
            "history": [],
        }
    }

    result = workflow_to_database(sample_workflow_data, existing_data)

    assert "history" in result["structured_data"]
    assert len(result["structured_data"]["history"]) == 1
    assert (
        result["structured_data"]["history"][0]["previous_data"]["concern_level"] == 2
    )


def test_database_to_workflow_conversion(sample_database_data: Dict[str, Any]) -> None:
    """Test conversion from database to workflow format."""
    result = database_to_workflow(sample_database_data)

    assert "tags" in result
    assert "summary" in result
    assert isinstance(result["tags"]["confidence_score"], float)
    assert 0 <= result["tags"]["confidence_score"] <= 1


def test_database_to_workflow_missing_data() -> None:
    """Test conversion with missing database fields."""
    invalid_data: Dict[str, Any] = {"structured_data": {}}
    with pytest.raises(KeyError):
        database_to_workflow(invalid_data)


def test_risk_score_calculation(sample_workflow_data: Dict[str, Any]) -> None:
    """Test risk score calculation logic."""
    result = workflow_to_database(sample_workflow_data)

    assert isinstance(result["risk_score"], int)
    assert 1 <= result["risk_score"] <= 5


def test_data_processor_error_handling() -> None:
    """Test error handling in data processor."""
    processor = DataProcessor()

    with pytest.raises(ValueError):
        processor.process(None)

    with pytest.raises(TypeError):
        processor.process({"tags": None, "summary": None})


def test_workflow_conversion_error_handling() -> None:
    """Test error handling in conversion functions."""
    with pytest.raises(KeyError):
        workflow_to_database({})

    with pytest.raises(KeyError):
        database_to_workflow({})


@pytest.mark.parametrize(
    "source_text,expected_type",
    [
        ("api_data_source", "api_data"),
        ("research_report", "research_data"),
        ("unknown_source", "unknown"),
    ],
)
def test_source_type_detection(source_text: str, expected_type: str) -> None:
    """Test source type detection logic."""
    processor = DataProcessor()
    result = processor.process({"content": "test", "source": source_text})
    assert result["metadata"]["source_type"] == expected_type
```
