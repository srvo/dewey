import pytest
from pathlib import Path
import sqlite3
from typing import List, Dict
from dewey.core.crm.transcripts.transcript_matching import match_transcript_files

# Fixtures for test setup
@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database with test episodes."""
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute('''
        CREATE TABLE episodes (
            title TEXT,
            file TEXT,
            transcript TEXT,
            link TEXT,
            publish_date DATE
        )
    ''')
    # Insert test episodes
    cursor.executemany('''
        INSERT INTO episodes (title, file, transcript, link, publish_date)
        VALUES (?, ?, ?, ?, ?)
    ''', [
        ("Test Episode 1", None, "Sample transcript 1", "https://example.com/1", "2023-01-01"),
        ("Test Episode 2", None, "Sample transcript 2", "https://example.com/2", "2023-01-02"),
    ])
    con.commit()
    con.close()
    return db_path

@pytest.fixture
def transcript_dir(tmp_path):
    """Create a temporary directory with test transcript files."""
    dir_path = tmp_path / "transcripts"
    dir_path.mkdir()
    # Create test files
    (dir_path / "Test Episode 1.txt").write_text("Sample transcript 1 content")
    (dir_path / "Test Episode 2.srt").write_text("Sample transcript 2 content")
    (dir_path / "Unrelated File.pdf").write_text("Invalid transcript format")
    return dir_path

# Test cases
def test_match_transcript_files_happy_path(temp_db, transcript_dir):
    """Test successful matching of transcripts with default parameters."""
    expected_matches = [
        {
            "title": "Test Episode 1",
            "file": str(transcript_dir / "Test Episode 1.txt"),
            "score": 1.0,
            "link": "https://example.com/1",
            "publish_date": "2023-01-01",
        },
        {
            "title": "Test Episode 2",
            "file": str(transcript_dir / "Test Episode 2.srt"),
            "score": 1.0,
            "link": "https://example.com/2",
            "publish_date": "2023-01-02",
        }
    ]
    matches, unmatched = match_transcript_files(
        str(temp_db),
        str(transcript_dir),
        update_db=False
    )
    assert matches == expected_matches
    assert len(unmatched) == 1  # Unrelated File.pdf

def test_database_update(temp_db, transcript_dir):
    """Verify database updates when update_db=True."""
    match_transcript_files(str(temp_db), str(transcript_dir), update_db=True)
    con = sqlite3.connect(temp_db)
    cursor = con.cursor()
    cursor.execute("SELECT file FROM episodes WHERE title=?", ("Test Episode 1",))
    assert cursor.fetchone()[0] == str(transcript_dir / "Test Episode 1.txt")

def test_similarity_threshold(temp_db, transcript_dir):
    """Test threshold filtering with intentionally mismatched filenames."""
    (transcript_dir / "Mismatched.txt").write_text("Mismatched content")
    matches, _ = match_transcript_files(
        str(temp_db),
        str(transcript_dir),
        similarity_threshold=0.9
    )
    assert len(matches) == 2  # Original matches still present

def test_error_conditions(temp_db, transcript_dir):
    """Test error handling for invalid database paths and file encodings."""
    # Test non-existent database
    _, unmatched = match_transcript_files("/invalid/path", transcript_dir)
    assert not unmatched

    # Test invalid encoding
    (transcript_dir / "invalid.txt").write_bytes(b'\xff')
    _, unmatched = match_transcript_files(str(temp_db), str(transcript_dir))
    assert str(transcript_dir / "invalid.txt") in unmatched

def test_truncation(temp_db, transcript_dir):
    """Test max_matches and unmatched_limit parameters."""
    for i in range(10):
        (transcript_dir / f"Extra{i}.txt").write_text("Extra content")
    matches, unmatched = match_transcript_files(
        str(temp_db),
        str(transcript_dir),
        max_matches=3,
        unmatched_limit=2
    )
    assert len(matches) == 3
    assert len(unmatched) == 2

# Additional tests for edge cases and Ibis integration would follow here
