\"\"\"
Functions for matching transcript files to episode entries in a database.
\"\"\"
import re
import os
import sqlite3
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional, Union
from pathlib import Path
from dewey.core.base_script import BaseScript

# Define a type alias for database connection
DBConnection = sqlite3.Connection

class TranscriptMatcher(BaseScript):
    def __init__(self):
        super().__init__(config_section='crm')

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
        encoding: str = self.config.get("encoding", "utf-8"),
        similarity_threshold: float = self.config.get("similarity_threshold", 0.7),
        max_matches: int = self.config.get("max_matches", 5),
        unmatched_limit: int = self.config.get("unmatched_limit", 5),
        update_db: bool = self.config.get("update_db", True),
    ) -> Tuple[List[Dict[str, Union[str, float]]], List[str]]:
        \"\""Matches transcript files to episode entries in a database.

        Args:
            database_path: The path to the SQLite database file.
            transcript_directory: The directory containing the transcript files.
            episode_table_name: The name of the table containing episode data. Defaults to "episodes".
            title_column: The name of the column containing the episode title. Defaults to "title".
            file_column: The name of the column containing the episode file path. Defaults to "file".
            transcript_column: The name of the column containing the episode transcript. Defaults to "transcript".
            link_column: The name of the column containing the episode link. Defaults to "link".
            publish_column: The name of the column containing the episode publish date. Defaults to "publish_date".
            encoding: The encoding to use when reading transcript files. Defaults to "utf-8".
            similarity_threshold: The minimum similarity score required for a match. Defaults to 0.7.
            max_matches: The maximum number of matches to return for each transcript. Defaults to 5.
            unmatched_limit: The maximum number of unmatched files to return. Defaults to 5.
            update_db: Whether to update the database with the matched file paths. Defaults to True.

        Returns:
            A tuple containing two lists:
                - matches: A list of dictionaries, where each dictionary represents a matched transcript
                  and contains keys like "title", "file", "score", and potentially other episode data.
                - unmatched_files: A list of file paths for transcripts that could not be matched.
        \"\""
        matches: List[Dict[str, Union[str, float]]] = []
        unmatched_files: List[str] = []

        try:
            database_path = Path(database_path)
            transcript_directory = Path(transcript_directory)

            with sqlite3.connect(str(database_path)) as con:
                cursor = con.cursor()

                # Fetch all episodes from the database
                cursor.execute(f"SELECT {title_column}, {file_column}, {transcript_column}, {link_column}, {publish_column} FROM {episode_table_name}")
                episodes = cursor.fetchall()
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
                    if not file_name.endswith((".txt", ".srt", ".vtt")):  # Consider common transcript extensions
                        continue

                    file_path = transcript_directory / file_name
                    try:
                        with open(file_path, "r", encoding=encoding) as transcript_file:
                            transcript = transcript_file.read()
                    except (IOError, UnicodeDecodeError) as e:
                        self.logger.error(f"Error reading {file_name}: {e}")
                        unmatched_files.append(str(file_path))
                        continue

                    best_match: Optional[Dict[str, Union[str, float]]] = None
                    best_score: float = 0.0

                    # Find the best match for the current transcript
                    for episode in episode_data:
                        if not episode["title"]:
                            continue  # Skip episodes with empty titles

                        title = episode["title"]
                        clean_title_episode = self.clean_title(title)
                        clean_title_file = self.clean_title(file_name)

                        score = self.similarity_score(clean_title_episode, clean_title_file)
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
                                cursor.execute(
                                    f"UPDATE {episode_table_name} SET {file_column} = ? WHERE {title_column} = ?",
                                    (str(file_path), best_match["title"]),
                                )
                            except sqlite3.Error as e:
                                self.logger.error(f"Error updating database for {best_match['title']}: {e}")
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
        \"\""Cleans the title by removing special characters and converting to lowercase.

        Args:
            title: The title to clean.

        Returns:
            The cleaned title.
        \"\""
        title = re.sub(r"[^a-zA-Z0-9\s]", "", title)  # Remove special characters
        title = title.lower()  # Convert to lowercase
        return title

    def similarity_score(self, title1: str, title2: str) -> float:
        \"\""Calculates the similarity score between two titles.

        Args:
            title1: The first title.
            title2: The second title.

        Returns:
            The similarity score between the two titles.
        \"\""
        return SequenceMatcher(None, title1, title2).ratio()