"""Unit tests for the transcript matching module."""
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
 from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.transcripts.transcript_matching import TranscriptMatcher


@pytest.fixture
def transcript_matcher() -> TranscriptMatcher:
    """Fixture to create a TranscriptMatcher instance."""
    return TranscriptMatcher()


@pytest.fixture
def mock_config(transcript_matcher: TranscriptMatcher) -> MagicMock:
    """Fixture to mock the configuration values."""
    mock = MagicMock()
    transcript_matcher.get_config_value = mock
    return mock


@pytest.fixture
def mock_db_connection() -> MagicMock:
    """Fixture to mock the database connection."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_cursor() -> MagicMock:
    """Fixture to mock the database cursor."""
    mock = MagicMock()
    return mock


@pytest.fixture
def test_database(tmp_path: Path) -> Path:
    """Fixture to create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_db.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE episodes (
            title TEXT,
            file TEXT,
            transcript TEXT,
            link TEXT,
            publish_date TEXT
        )
    """
    )
    cursor.execute(
        "INSERT INTO episodes (title, file, transcript, link, publish_date) VALUES (?, ?, ?, ?, ?)",
        (
            "Test Episode 1",
            None,
            None,
            "http://example.com/episode1",
            "2024-01-01",
        ),
    )
    cursor.execute(
        "INSERT INTO episodes (title, file, transcript, link, publish_date) VALUES (?, ?, ?, ?, ?)",
        (
            "Test Episode 2",
            None,
            None,
            "http://example.com/episode2",
            "2024-01-02",
        ),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def test_transcript_directory(tmp_path: Path) -> Path:
    """Fixture to create a temporary directory with transcript files."""
    transcript_dir = tmp_path / "transcripts"
    transcript_dir.mkdir()
    (transcript_dir / "test_episode_1.txt").write_text("This is the transcript for test episode 1.")
    (transcript_dir / "test_episode_2.txt").write_text("This is the transcript for test episode 2.")
    (transcript_dir / "ignore_me.pdf").write_text("ignore this file")
    return transcript_dir


def test_transcript_matcher_initialization(transcript_matcher: TranscriptMatcher) -> None:
    """Test that the TranscriptMatcher is initialized correctly."""
    assert transcript_matcher.name == "TranscriptMatcher"
    assert transcript_matcher.config_section == "crm"


@patch("dewey.core.crm.transcripts.transcript_matching.os.listdir")
@patch("dewey.core.crm.transcripts.transcript_matching.sqlite3.connect")
def test_match_transcript_files_success(
    mock_connect: MagicMock,
    mock_listdir: MagicMock,
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test successful matching of transcript files to episodes."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]
    mock_listdir.return_value = ["test_episode_1.txt", "test_episode_2.txt"]
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
        ("Test Episode 2", None, None, "http://example.com/episode2", "2024-01-02"),
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

    matches, unmatched_files = transcript_matcher.match_transcript_files(
        database_path=str(test_database),
        transcript_directory=str(test_transcript_directory),
    )

    assert len(matches) == 2
    assert len(unmatched_files) == 0
    assert matches[0]["title"] == "Test Episode 1"
    assert matches[1]["title"] == "Test Episode 2"
    assert Path(str(matches[0]["file"])).name == "test_episode_1.txt"
    assert Path(str(matches[1]["file"])).name == "test_episode_2.txt"


@patch("dewey.core.crm.transcripts.transcript_matching.os.listdir")
@patch("dewey.core.crm.transcripts.transcript_matching.sqlite3.connect")
def test_match_transcript_files_no_match(
    mock_connect: MagicMock,
    mock_listdir: MagicMock,
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test scenario where no transcript files match any episodes."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.9,  # High similarity threshold
        5,
        5,
        True,
    ]
    mock_listdir.return_value = ["test_episode_1.txt", "test_episode_2.txt"]
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
        ("Test Episode 2", None, None, "http://example.com/episode2", "2024-01-02"),
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

    matches, unmatched_files = transcript_matcher.match_transcript_files(
        database_path=str(test_database),
        transcript_directory=str(test_transcript_directory),
    )

    assert len(matches) == 0
    assert len(unmatched_files) == 2
    assert Path(unmatched_files[0]).name == "test_episode_1.txt"
    assert Path(unmatched_files[1]).name == "test_episode_2.txt"


@patch("dewey.core.crm.transcripts.transcript_matching.os.listdir")
@patch("dewey.core.crm.transcripts.transcript_matching.sqlite3.connect")
def test_match_transcript_files_file_not_found_error(
    mock_connect: MagicMock,
    mock_listdir: MagicMock,
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
) -> None:
    """Test handling of FileNotFoundError when the transcript directory is not found."""
    mock_config.side_effect = [
        str(test_database),
        "/path/that/does/not/exist",
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]
    mock_listdir.return_value = []
    mock_connect.return_value.__enter__.return_value.cursor.return_value = MagicMock()

    matches, unmatched_files = transcript_matcher.match_transcript_files(
        database_path=str(test_database),
        transcript_directory="/path/that/does/not/exist",
    )

    assert len(matches) == 0
    assert len(unmatched_files) == 0


@patch("dewey.core.crm.transcripts.transcript_matching.os.listdir")
@patch("dewey.core.crm.transcripts.transcript_matching.sqlite3.connect")
def test_match_transcript_files_database_error(
    mock_connect: MagicMock,
    mock_listdir: MagicMock,
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_transcript_directory: Path,
) -> None:
    """Test handling of sqlite3.Error when a database error occurs."""
    mock_config.side_effect = [
        "/path/that/does/not/exist",
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]
    mock_listdir.return_value = []
    mock_connect.side_effect = sqlite3.Error("Simulated database error")

    matches, unmatched_files = transcript_matcher.match_transcript_files(
        database_path="/path/that/does/not/exist",
        transcript_directory=str(test_transcript_directory),
    )

    assert len(matches) == 0
    assert len(unmatched_files) == 0


@patch("dewey.core.crm.transcripts.transcript_matching.os.listdir")
@patch("dewey.core.crm.transcripts.transcript_matching.sqlite3.connect")
def test_match_transcript_files_io_error(
    mock_connect: MagicMock,
    mock_listdir: MagicMock,
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test handling of IOError when there's an error reading a transcript file."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]
    mock_listdir.return_value = ["test_episode_1.txt"]
    mock_connect.return_value.__enter__.return_value.cursor.return_value = MagicMock()

    # Mock the open function to raise an IOError
    with patch("builtins.open", side_effect=IOError("Simulated IO error")):
        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

    assert len(matches) == 0
    assert len(unmatched_files) == 1
    assert Path(unmatched_files[0]).name == "test_episode_1.txt"


def test_clean_title(transcript_matcher: TranscriptMatcher) -> None:
    """Test the clean_title method to remove special characters and lowercase titles."""
    title = "Test Episode!@#$%^&*()_+=-`~[]\{}|;':\",./<>?"
    cleaned_title = transcript_matcher.clean_title(title)
    assert cleaned_title == "test episode"


@pytest.mark.parametrize(
    "title1, title2, expected_score",
    [
        ("test episode 1", "test episode 1", 1.0),
        ("test episode 1", "test episode 2", 0.8888888888888888),
        ("test episode", "different title", 0.0),
    ],
)
def test_similarity_score(
    transcript_matcher: TranscriptMatcher, title1: str, title2: str, expected_score: float
) -> None:
    """Test the similarity_score method with different titles."""
    score = transcript_matcher.similarity_score(title1, title2)
    assert score == expected_score


@patch("dewey.core.crm.transcripts.transcript_matching.TranscriptMatcher.match_transcript_files")
def test_run(
    mock_match_transcript_files: MagicMock,
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
) -> None:
    """Test the run method to execute the transcript matching process."""
    mock_config.side_effect = [
        "database_path",
        "transcript_directory",
        "episode_table_name",
        "title_column",
        "file_column",
        "transcript_column",
        "link_column",
        "publish_column",
        "encoding",
        0.7,
        5,
        5,
        True,
    ]
    mock_match_transcript_files.return_value = ([], [])

    transcript_matcher.run()

    mock_match_transcript_files.assert_called_once_with(
        database_path="database_path",
        transcript_directory="transcript_directory",
        episode_table_name="episode_table_name",
        title_column="title_column",
        file_column="file_column",
        transcript_column="transcript_column",
        link_column="link_column",
        publish_column="publish_column",
        encoding="encoding",
        similarity_threshold=0.7,
        max_matches=5,
        unmatched_limit=5,
        update_db=True,
    )


def test_match_transcript_files_unmatched_limit(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test that the unmatched_limit parameter limits the number of unmatched files returned."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.9,  # High similarity threshold
        5,
        1,  # unmatched_limit = 1
        True,
    ]

    # Create more transcript files than the unmatched_limit
    (test_transcript_directory / "test_episode_3.txt").write_text(
        "This is the transcript for test episode 3."
    )
    (test_transcript_directory / "test_episode_4.txt").write_text(
        "This is the transcript for test episode 4."
    )

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = [
            "test_episode_1.txt",
            "test_episode_2.txt",
            "test_episode_3.txt",
            "test_episode_4.txt",
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
            ("Test Episode 2", None, None, "http://example.com/episode2", "2024-01-02"),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

    assert len(matches) == 0
    assert len(unmatched_files) == 1  # Should be limited to 1
    assert Path(unmatched_files[0]).name == "test_episode_1.txt"


def test_match_transcript_files_max_matches(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test that the max_matches parameter limits the number of matched files returned."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.1,  # Low similarity threshold
        1,  # max_matches = 1
        5,
        True,
    ]

    # Create more transcript files than the max_matches
    (test_transcript_directory / "test_episode_3.txt").write_text(
        "This is the transcript for test episode 3."
    )
    (test_transcript_directory / "test_episode_4.txt").write_text(
        "This is the transcript for test episode 4."
    )

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = [
            "test_episode_1.txt",
            "test_episode_2.txt",
            "test_episode_3.txt",
            "test_episode_4.txt",
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
            ("Test Episode 2", None, None, "http://example.com/episode2", "2024-01-02"),
            ("Test Episode 3", None, None, "http://example.com/episode3", "2024-01-03"),
            ("Test Episode 4", None, None, "http://example.com/episode4", "2024-01-04"),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

    assert len(matches) == 1  # Should be limited to 1
    assert len(unmatched_files) == 0
    assert matches[0]["title"] == "Test Episode 1"


def test_match_transcript_files_update_db_false(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test that the database is not updated when update_db is False."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.1,  # Low similarity threshold
        5,
        5,
        False,  # update_db = False
    ]

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = ["test_episode_1.txt"]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

        assert len(matches) == 1
        assert len(unmatched_files) == 0
        mock_cursor.execute.assert_not_called()  # Ensure the database is not updated


def test_match_transcript_files_transcript_extensions(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test that only files with .txt, .srt, or .vtt extensions are processed."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.1,
        5,
        5,
        True,
    ]

    # Create files with different extensions
    (test_transcript_directory / "test_episode_1.txt").write_text(
        "This is the transcript for test episode 1."
    )
    (test_transcript_directory / "test_episode_1.srt").write_text(
        "This is the transcript for test episode 1."
    )
    (test_transcript_directory / "test_episode_1.vtt").write_text(
        "This is the transcript for test episode 1."
    )
    (test_transcript_directory / "test_episode_1.pdf").write_text(
        "This is not a transcript file."
    )

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = [
            "test_episode_1.txt",
            "test_episode_1.srt",
            "test_episode_1.vtt",
            "test_episode_1.pdf",
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

        assert len(matches) == 3  # Only .txt, .srt, and .vtt should be matched
        assert len(unmatched_files) == 0
        # Ensure the database is updated for the matched files
        assert mock_cursor.execute.call_count == 3


def test_match_transcript_files_unicode_decode_error(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test handling of UnicodeDecodeError when there's an error decoding a transcript file."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]

    # Create a file with invalid UTF-8 encoding
    (test_transcript_directory / "test_episode_1.txt").write_bytes(b"\xff\xfe\xfd")

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = ["test_episode_1.txt"]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

        assert len(matches) == 0
        assert len(unmatched_files) == 1
        assert Path(unmatched_files[0]).name == "test_episode_1.txt"


def test_match_transcript_files_empty_title(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test that episodes with empty titles are skipped."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = ["test_episode_1.txt"]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("", None, None, "http://example.com/episode1", "2024-01-01"),  # Empty title
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        matches, unmatched_files = transcript_matcher.match_transcript_files(
            database_path=str(test_database),
            transcript_directory=str(test_transcript_directory),
        )

        assert len(matches) == 0
        assert len(unmatched_files) == 1  # File should be unmatched due to empty title


def test_match_transcript_files_unexpected_error(
    transcript_matcher: TranscriptMatcher,
    mock_config: MagicMock,
    test_database: Path,
    test_transcript_directory: Path,
) -> None:
    """Test handling of unexpected exceptions during the matching process."""
    mock_config.side_effect = [
        str(test_database),
        str(test_transcript_directory),
        "episodes",
        "title",
        "file",
        "transcript",
        "link",
        "publish_date",
        "utf-8",
        0.7,
        5,
        5,
        True,
    ]

    with patch("dewey.core.crm.transcripts.transcript_matching.os.listdir") as mock_listdir, patch(
        "dewey.core.crm.transcripts.transcript_matching.sqlite3.connect"
    ) as mock_connect:
        mock_listdir.return_value = ["test_episode_1.txt"]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Episode 1", None, None, "http://example.com/episode1", "2024-01-01"),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Mock the similarity_score method to raise an exception
        with patch(
            "dewey.core.crm.transcripts.transcript_matching.TranscriptMatcher.similarity_score",
            side_effect=Exception("Simulated unexpected error"),
        ):
            matches, unmatched_files = transcript_matcher.match_transcript_files(
                database_path=str(test_database),
                transcript_directory=str(test_transcript_directory),
            )

        assert len(matches) == 0
        assert len(unmatched_files) == 0  # All files should be unmatched due to the error
