import feedparser
import pandas as pd
from datetime import datetime
import os

def fetch_ir_feeds(tickers: list = None):
    """
    Fetch IR RSS feeds for a list of tickers
    
    Args:
        tickers (list): List of stock tickers. Defaults to test tickers if None.
    """
    if tickers is None:
        tickers = ['AAPL', 'MSFT']  # Test tickers
        
    results = []
    
    # Common IR RSS patterns
    ir_patterns = [
        "https://ir.{}.com/rss/news-releases.xml",
        "https://investors.{}.com/rss/news.xml",
        "https://ir.{}.com/feed/",
        "https://investor.{}.com/rss"
    ]
    
    for ticker in tickers:
        print(f"Fetching feeds for {ticker}...")
        for pattern in ir_patterns:
            try:
                url = pattern.format(ticker.lower())
                feed = feedparser.parse(url)
                
                if feed.entries:
                    for entry in feed.entries:
                        results.append({
                            'ticker': ticker,
                            'title': entry.title,
                            'link': entry.link,
                            'published': entry.get('published', ''),
                            'summary': entry.get('summary', ''),
                            'source_url': url
                        })
                    print(f"Found {len(feed.entries)} entries for {ticker}")
                    break  # Found working feed, move to next ticker
                    
            except Exception as e:
                print(f"Error fetching {ticker} from {url}: {str(e)}")
                continue
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    # Test run
    df = fetch_ir_feeds()
    print("\nResults:")
    print(df.head())
