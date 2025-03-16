from __future__ import annotations

import asyncio
from datetime import datetime

import aiohttp
import feedparser
import pandas as pd


class RSSFeed:
    def __init__(
        self,
        title: str,
        url: str,
        last_updated: datetime | None = None,
    ) -> None:
        self.title = title
        self.url = url
        self.last_updated = last_updated
        self.entries: list[dict] = []

    async def fetch(self) -> None:
        """Fetch the RSS feed asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        self.entries = feed.entries[:10]  # Keep last 10 entries
                        if feed.feed.get("updated_parsed"):
                            self.last_updated = datetime(*feed.feed.updated_parsed[:6])
                    else:
                        pass
        except Exception:
            pass


class RSSManager:
    def __init__(self, universe_df: pd.DataFrame) -> None:
        self.universe_df = universe_df
        self.feeds: dict[str, RSSFeed] = {}
        self.initialize_feeds()

    def initialize_feeds(self) -> None:
        """Initialize RSS feeds from universe data."""
        # Add default financial news feeds
        self.feeds["Financial Times"] = RSSFeed(
            "Financial Times",
            "https://www.ft.com/rss/home",
        )
        self.feeds["WSJ Markets"] = RSSFeed(
            "WSJ Markets",
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        )

        # Add company-specific feeds from universe_df
        for _, row in self.universe_df.iterrows():
            ticker = row["Ticker"]
            if "RSS_Feed" in row and pd.notna(row["RSS_Feed"]):
                self.feeds[ticker] = RSSFeed(
                    f"{ticker} - {row['Security Name']}",
                    row["RSS_Feed"],
                )

    async def fetch_all(self) -> None:
        """Fetch all RSS feeds asynchronously."""
        tasks = [feed.fetch() for feed in self.feeds.values()]
        await asyncio.gather(*tasks)

    def get_latest_entries(
        self,
        feed_key: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get latest entries from specified feed or all feeds."""
        if feed_key and feed_key in self.feeds:
            return self.feeds[feed_key].entries[:limit]

        # Combine and sort entries from all feeds
        all_entries = []
        for feed in self.feeds.values():
            for entry in feed.entries:
                if hasattr(entry, "published_parsed"):
                    entry["feed_title"] = feed.title
                    all_entries.append(entry)

        # Sort by published date
        all_entries.sort(
            key=lambda x: (
                datetime(*x.published_parsed[:6])
                if hasattr(x, "published_parsed")
                else datetime.min
            ),
            reverse=True,
        )
        return all_entries[:limit]

    def get_company_news(self, ticker: str, limit: int = 5) -> list[dict]:
        """Get latest news for a specific company."""
        if ticker in self.feeds:
            return self.feeds[ticker].entries[:limit]
        return []
