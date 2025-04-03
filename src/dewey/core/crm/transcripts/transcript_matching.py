"""Functions for matching transcript files to episode entries in a database."""

import os
import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from dewey.core.base_script import BaseScript
from dewey.core.db.utils import execute_query

# Define a type alias for database connection


class TranscriptMatcher(BaseScript):
    """Matches transcript files to episode entries in a database."""

    def __init__(self) -> None:
        """Initializes the TranscriptMatcher with CRM configuration."""
        super().__init__(config_section="crm")

    def run(self) -> None:
        """Executes the transcript matching process."""
        database_path = self.get_config_value("database_path")
        transcript_directory = self.get_config_value("transcript_directory")
        episode_table_name = self.get_config_value("episode_table_name", "episodes")
        title_column = self.get_config_value("title_column", "title")
        file_column = self.get_config_value("file_column", "file")
        transcript_column = self.get_config_value("transcript_column", "transcript")
        link_column = self.get_config_value("link_column", "link")
        publish_column = self.get_config_value("publish_column", "publish_date")
        encoding = self.get_config_value("encoding", "utf-8")
        similarity_threshold = self.get_config_value("similarity_threshold", 0.7)
        max_matches = self.get_config_value("max_matches", 5)
        unmatched_limit = self.get_config_value("unmatched_limit", 5)
        update_db = self.get_config_value("update_db", True)

        matches, unmatched_files = self.match_transcript_files(
            database_path=database_path,
            transcript_directory=transcript_directory,
            episode_table_name=episode_table_name,
            title_column=title_column,
            file_column=file_column,
            transcript_column=transcript_column,
            link_column=link_column,
            publish_column=publish_column,
            encoding=encoding,
            similarity_threshold=similarity_threshold,
            max_matches=max_matches,
            unmatched_limit=unmatched_limit,
            update_db=update_db,
        )

        self.logger.info(f"Matched {len(matches)} transcripts.")
        self.logger.info(f"Unmatched files: {unmatched_files}")

    def match_transcript_files(
        self,
        database_path: str,
        transcript_directory: str,
        episode_table_name: str = "episodes",
        title_column: str = "title",
        file_column: str = "file",
        transcript_column: str = "transcript",
        link_column: str = "link",
        publish_column: str = "publish_date",
        encoding: str = "utf-8",
        similarity_threshold: float = 0.7,
        max_matches: int = 5,
        unmatched_limit: int = 5,
        update_db: bool = True,
    ) -> tuple[list[dict[str, str | float]], list[str]]:
        """Matches transcript files to episode entries in a database.

        Args:
            database_path: The path to the SQLite database file.
            transcript_directory: The directory containing the transcript files.
            episode_table_name: The name of the table containing episode data.
            title_column: The name of the column containing the episode title.
            file_column: The name of the column containing the episode file path.
            transcript_column: The name of the column containing the episode transcript.
            link_column: The name of the column containing the episode link.
            publish_column: The name of the column containing the episode publish date.
            encoding: The encoding to use when reading transcript files.
            similarity_threshold: The minimum similarity score required for a match.
            max_matches: The maximum number of matches to return for each transcript.
            unmatched_limit: The maximum number of unmatched files to return.
            update_db: Whether to update the database with the matched file paths.

        Returns:
            A tuple containing two lists:
                - matches: A list of dictionaries, where each dictionary represents a matched transcript
                  and contains keys like "title", "file", "score", and potentially other episode data.
                - unmatched_files: A list of file paths for transcripts that could not be matched.

        Raises:
            FileNotFoundError: If the database or transcript directory is not found.
            sqlite3.Error: If there is an error executing a database query.
            IOError: If there is an error reading a transcript file.
            UnicodeDecodeError: If there is an error decoding a transcript file.

        """
        matches: list[dict[str, str | float]] = []
        unmatched_files: list[str] = []

        try:
            database_path = Path(database_path)
            transcript_directory = Path(transcript_directory)

            with sqlite3.connect(str(database_path)) as con:
                cursor = con.cursor()

                # Fetch all episodes from the database
                query = f"SELECT {title_column}, {file_column}, {transcript_column}, {link_column}, {publish_column} FROM {episode_table_name}"
                episodes = execute_query(cursor, query)
                episode_data = [
                    {
                        "title": row[0],
                        "file": row[1],
                        "transcript": row[2],
                        "link": row[3],
                        "publish_date": row[4],
                    }
                    for row in episodes
                ]

                # Iterate through transcript files
                for file_name in os.listdir(transcript_directory):
                    if not file_name.endswith(
                        (".txt", ".srt", ".vtt")
                    ):  # Consider common transcript extensions
                        continue

                    file_path = transcript_directory / file_name
                    try:
                        with open(file_path, encoding=encoding) as transcript_file:
                            transcript = transcript_file.read()
                    except (OSError, UnicodeDecodeError) as e:
                        self.logger.error(f"Error reading {file_name}: {e}")
                        unmatched_files.append(str(file_path))
                        continue

                    best_match: dict[str, str | float] | None = None
                    best_score: float = 0.0

                    # Find the best match for the current transcript
                    for episode in episode_data:
                        if not episode["title"]:
                            continue  # Skip episodes with empty titles

                        title = episode["title"]
                        clean_title_episode = self.clean_title(title)
                        clean_title_file = self.clean_title(file_name)

                        score = self.similarity_score(
                            clean_title_episode, clean_title_file
                        )
                        if score > best_score:
                            best_score = score
                            best_match = episode
                            best_match["file"] = str(file_path)  # Store the file path

                    # Handle the match
                    if best_match and best_score >= similarity_threshold:
                        match = {
                            "title": best_match["title"],
                            "file": str(file_path),
                            "score": best_score,
                            "link": best_match["link"],
                            "publish_date": best_match["publish_date"],
                        }
                        matches.append(match)

                        if update_db:
                            try:
                                # Update the database with the file path
                                update_query = f"UPDATE {episode_table_name} SET {file_column} = ? WHERE {title_column} = ?"
                                cursor.execute(
                                    update_query, (str(file_path), best_match["title"])
                                )
                                con.commit()
                            except sqlite3.Error as e:
                                self.logger.error(
                                    f"Error updating database for {best_match['title']}: {e}"
                                )
                    else:
                        unmatched_files.append(str(file_path))

        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return [], []  # Return empty lists on database error
        except FileNotFoundError:
            self.logger.error(f"Database file not found: {database_path}")
            return [], []
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            return [], []

        return matches[:max_matches], unmatched_files[:unmatched_limit]

    def clean_title(self, title: str) -> str:
        """Cleans the title by removing special characters and converting to lowercase.

        Args:
            title: The title to clean.

        Returns:
            The cleaned title.

        """
        title = re.sub(r"[^a-zA-Z0-9\s]", "", title)  # Remove special characters
        title = title.lower()  # Convert to lowercase
        return title

    def similarity_score(self, title1: str, title2: str) -> float:
        """Calculates the similarity score between two titles.

        Args:
            title1: The first title.
            title2: The second title.

        Returns:
            The similarity score between the two titles.

        """
        return SequenceMatcher(None, title1, title2).ratio()


if __name__ == "__main__":
    matcher = TranscriptMatcher()
    matcher.execute()
