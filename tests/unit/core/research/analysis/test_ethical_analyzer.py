import pytest
import os
import logging
import pandas as pd
from unittest.mock import patch
from dewey.core.research.analysis.ethical_analyzer import EthicalAnalyzer
import datetime
import json


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with sample exclude.csv."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "Company": "Test Corp",
                "Symbol": "TEST",
                "Category": "Test Category",
                "Criteria": "Test Criteria",
            }
        ]
    )
    df.to_csv(data_dir / "exclude.csv", index=False)
    return data_dir


@pytest.fixture
def mock_rclone_config(tmp_path):
    """Mock rclone config path to a temporary location."""
    config_path = tmp_path / "rclone.conf"
    with patch(
        "dewey.core.research.analysis.ethical_analyzer.Path.home", return_value=tmp_path
    ):
        yield config_path


@pytest.fixture
def analyzer(tmp_data_dir, mock_rclone_config):
    """Provide an EthicalAnalyzer instance with temporary data directory."""
    return EthicalAnalyzer(data_dir=tmp_data_dir)


def test_setup_analysis_tables(analyzer):
    """Verify analysis tables are created properly."""
    with analyzer.get_connection() as conn:
        tables = conn.execute("SHOW TABLES").fetchall()
        assert "ethical_analysis" in tables
        assert "company_ethical_profile" in tables


def test_generate_analysis_prompt(analyzer):
    """Check prompt generation for valid company data."""
    company_row = {
        "Company": "Test Corp",
        "Symbol": "TEST",
        "Category": "Product-based",
        "Criteria": "Animal Cruelty",
    }
    prompt = analyzer.generate_analysis_prompt(company_row)
    assert "Test Corp (TEST)" in prompt
    assert "Current primary exclusion: Product-based - Animal Cruelty" in prompt
    assert "HISTORICAL ANALYSIS (40%)" in prompt


def test_save_analysis_json(analyzer):
    """Test JSON saving and S3 sync functionality."""
    company_data = {"test": "data"}
    timestamp = datetime.datetime.now()
    analyzer.save_analysis_json(company_data, timestamp)
    json_dir = analyzer.data_dir / "analysis_json"
    assert json_dir.exists()
    json_files = list(json_dir.glob("ethical_analysis_*.json"))
    assert len(json_files) == 1
    with open(json_files[0], "r") as f:
        saved_data = json.load(f)
    assert saved_data == company_data


def test_run_analysis(analyzer):
    """Verify successful analysis execution with sample data."""
    analysis_results = analyzer.run_analysis()
    assert analysis_results["meta"]["type"] == "ethical_analysis"
    assert len(analysis_results["companies"]) == 1
    company = analysis_results["companies"][0]
    assert company["name"] == "Test Corp"
    assert "analysis_prompt" in company


@pytest.fixture
def empty_analyzer(tmp_path):
    """Provide analyzer with empty exclude.csv."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    df = pd.DataFrame(columns=["Company", "Symbol", "Category", "Criteria"])
    df.to_csv(data_dir / "exclude.csv", index=False)
    return EthicalAnalyzer(data_dir=data_dir)


def test_run_analysis_empty_exclude(empty_analyzer, caplog):
    """Test handling of empty exclude.csv file."""
    empty_analyzer.run_analysis()
    assert "Found 0 companies to analyze" in caplog.text


def test_run_analysis_missing_file(tmp_path):
    """Check error handling when exclude.csv is missing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    analyzer = EthicalAnalyzer(data_dir=data_dir)
    with pytest.raises(FileNotFoundError):
        analyzer.run_analysis()
