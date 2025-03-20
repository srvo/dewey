import pytest
import duckdb
import os
import json
from pathlib import Path
from dewey.core.research.search_analysis_integration import (
    connect_to_motherduck,
    ensure_tables_exist,
    process_file,
    process_directory,
    process_company,
    process_risk_factors,
    process_evidence
)

@pytest.fixture
def tmp_duckdb(tmp_path):
    """Create temporary DuckDB connection (pytest fixture)."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    yield conn
    conn.close()

@pytest.fixture
def sample_json_file(tmp_path):
    """Create sample JSON test file (pytest fixture)."""
    data = {
        "meta": {
            "timestamp": "2023-01-01T00:00:00",
            "version": "1.0"
        },
        "companies": [
            {
                "company_name": "Test Corp",
                "symbol": "TEST",
                "analysis": {
                    "historical": {
                        "risk_score": 5,
                        "confidence_score": 80,
                        "recommendation": "Hold",
                        "key_risks": ["Risk1", "Risk2"],
                        "controversies": ["Cont1"],
                        "environmental_issues": ["Env1"],
                        "social_issues": ["Social1"],
                        "governance_issues": ["Gov1"]
                    },
                    "evidence": {
                        "sources": [
                            {
                                "url": "https://example.com",
                                "title": "Test Title",
                                "snippet": "Test Snippet",
                                "domain": "example.com",
                                "source_type": "web",
                                "category": "news",
                                "query_context": "context",
                                "retrieved_at": "2023-01-01T00:00:00",
                                "published_date": "2023-01-01T00:00:00",
                                "source_hash": "abc123"
                            }
                        ]
                    }
                }
            }
        ]
    }
    file_path = tmp_path / "search_analysis_valid.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path

def test_ensure_tables_exist(tmp_duckdb):
    """Verify table creation succeeds and logs properly."""
    conn = tmp_duckdb
    ensure_tables_exist(conn)
    tables = conn.execute("SHOW TABLES").fetchall()
    expected = ["search_analysis", "company_analysis", "company_risk_factors", "company_evidence"]
    for table in expected:
        assert (table,) in tables

def test_process_file_valid(tmp_duckdb, sample_json_file):
    """Test successful processing of valid JSON file."""
    conn = tmp_duckdb
    ensure_tables_exist(conn)
    process_file(str(sample_json_file), conn)
    
    # Verify search_analysis entry
    search_row = conn.execute("SELECT * FROM search_analysis").fetchone()
    assert search_row[0] == "search_analysis_valid"
    
    # Verify company_analysis entry
    company_row = conn.execute("SELECT * FROM company_analysis").fetchone()
    assert company_row[2] == "Test Corp"
    
    # Verify risk factors (5 types × 1 each)
    risk_count = conn.execute("SELECT COUNT(*) FROM company_risk_factors").fetchone()[0]
    assert risk_count == 5
    
    # Verify evidence entry
    evidence_count = conn.execute("SELECT COUNT(*) FROM company_evidence").fetchone()[0]
    assert evidence_count == 1

def test_process_file_missing_required(tmp_duckdb, tmp_path):
    """Test error handling for missing required fields."""
    invalid_file = tmp_path / "invalid.json"
    with open(invalid_file, "w") as f:
        json.dump({"meta": {}}, f)
        
    conn = tmp_duckdb
    with pytest.raises(Exception, match="Error processing file"):
        process_file(str(invalid_file), conn)

def test_process_directory(tmp_duckdb, tmp_path):
    """Verify directory processing with multiple files."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    
    # Create two valid files
    for i in range(2):
        file_path = dir_path / f"search_analysis_{i}.json"
        with open(file_path, "w") as f:
            json.dump({"meta": {}, "companies": []}, f)
    
    conn = tmp_duckdb
    ensure_tables_exist(conn)
    process_directory(str(dir_path), conn)
    
    # Verify processed two files
    file_count = conn.execute("SELECT COUNT(*) FROM search_analysis").fetchone()[0]
    assert file_count == 2

def test_process_risk_factors_update(tmp_duckdb, tmp_path):
    """Verify risk factors are deleted/replaced properly."""
    conn = tmp_duckdb
    ensure_tables_exist(conn)
    company_id = "TEST_UPDATE"
    
    # Initial insertion
    process_risk_factors(conn, company_id, {"key_risks": ["Old Risk"]})
    initial_count = conn.execute("SELECT COUNT(*) FROM company_risk_factors").fetchone()[0]
    assert initial_count == 1
    
    # Re-process with new data
    process_risk_factors(conn, company_id, {"key_risks": ["New Risk"]})
    final_count = conn.execute("SELECT COUNT(*) FROM company_risk_factors").fetchone()[0]
    assert final_count == 1  # Should have replaced existing

def test_evidence_deletion(tmp_duckdb, tmp_path):
    """Verify evidence is deleted before insertion."""
    conn = tmp_duckdb
    ensure_tables_exist(conn)
    company_id = "EVIDENCE_TEST"
    
    # First insertion
    process_evidence(conn, company_id, {"sources": [{"url": "old"}]})
    initial_count = conn.execute("SELECT COUNT(*) FROM company_evidence").fetchone()[0]
    assert initial_count == 1
    
    # Second insertion should replace
    process_evidence(conn, company_id, {"sources": [{"url": "new"}]})
    final_count = conn.execute("SELECT COUNT(*) FROM company_evidence").fetchone()[0]
    assert final_count == 1  # Only new entry remains

def test_missing_company_data(tmp_duckdb, tmp_path):
    """Test error handling for missing company analysis data."""
    invalid_data = {"company_name": "Test", "analysis": None}
    conn = tmp_duckdb
    
    with pytest.raises(Exception, match="Error processing company Test"):
        process_company(conn, "TEST", invalid_data)

def test_empty_evidence_list(tmp_duckdb, tmp_path):
    """Verify empty evidence lists are handled gracefully."""
    conn = tmp_duckdb
    ensure_tables_exist(conn)
    company_id = "EMPTY_EVIDENCE"
    
    # Process with empty evidence
    process_evidence(conn, company_id, {"sources": []})
    evidence_count = conn.execute("SELECT COUNT(*) FROM company_evidence").fetchone()[0]
    assert evidence_count == 0
