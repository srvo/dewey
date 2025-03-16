#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag


class PodcastDownloader:
    """A class to download podcast episodes from a specified website and save their metadata."""

    def __init__(self) -> None:
        """Initializes the PodcastDownloader with the base URL and output directory."""
        self.base_url = "https://freemoneypodcast.com"
        self.output_dir = "podcast_episodes"

    def _create_directory(self, directory_name: str) -> None:
        """Creates a directory if it does not already exist.

        Args:
        ----
            directory_name: The name of the directory to create.

        """
        path = os.path.join(self.output_dir, directory_name)
        os.makedirs(path, exist_ok=True)

    def setup_directories(self) -> None:
        """Creates the necessary directories for audio files, transcripts, and metadata."""
        dirs = ["audio", "transcripts", "metadata"]
        for directory in dirs:
            self._create_directory(directory)

    def get_episode_list(self) -> list[Tag]:
        """Fetches a list of all episodes from the podcast website.

        Returns
        -------
            A list of BeautifulSoup Tag objects representing the episodes.

        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        try:
            response = requests.get(f"{self.base_url}/s/the-podcast", headers=headers)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            soup = BeautifulSoup(response.text, "html.parser")

            # Find all episode links (adjust selectors based on the actual HTML structure)
            return soup.find_all("article", class_="post")

        except requests.exceptions.RequestException:
            return []

    def download_episode(self, episode_url: str, filename: str) -> str | None:
        """Downloads an individual episode from the given URL.

        Args:
        ----
            episode_url: The URL of the episode to download.
            filename: The filename to save the episode as.

        Returns:
        -------
            The filepath to the downloaded episode, or None if the download failed.

        """
        try:
            response = requests.get(episode_url, stream=True)
            response.raise_for_status()  # Raise HTTPError for bad responses
            filepath = os.path.join(self.output_dir, "audio", filename)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return filepath
        except requests.exceptions.RequestException:
            return None

    def save_metadata(self, episode_data: dict[str, Any]) -> None:
        """Saves episode metadata to a JSON file.

        Args:
        ----
            episode_data: A dictionary containing the episode metadata.

        """
        filepath = os.path.join(self.output_dir, "metadata", "episodes.json")

        try:
            if os.path.exists(filepath):
                with open(filepath) as f:
                    data: list[dict[str, Any]] = json.load(f)
            else:
                data = []

            data.append(episode_data)

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

        except Exception:
            pass


def main() -> None:
    """Main function to download podcast episodes and save their metadata."""
    downloader = PodcastDownloader()
    downloader.setup_directories()

    episodes = downloader.get_episode_list()

    for episode in episodes:
        # Extract episode details (adjust selectors as needed)
        title = episode.find("h2").text.strip()
        date = episode.find("time")["datetime"]
        audio_url = episode.find("audio")["src"]

        # Generate filename
        filename = f"{date}_{re.sub(r'[^\w\\-_]', '_', title)}.mp3"

        # Download episode
        filepath = downloader.download_episode(audio_url, filename)

        if filepath:
            # Save metadata
            metadata = {
                "title": title,
                "date": date,
                "audio_url": audio_url,
                "local_path": filepath,
                "downloaded_at": datetime.now().isoformat(),
            }
            downloader.save_metadata(metadata)


if __name__ == "__main__":
    main()
