"""Engines Package
==============

Provides various data access and processing engines for the Dewey system.
"""

from .base import BaseEngine, SearchEngine

# Database engines
from .motherduck import MotherDuckEngine

# Temporarily comment out other imports until syntax errors are fixed
# Financial engines
# from .fmp_engine import FMPEngine
# from .yahoo_finance_engine import YahooFinanceEngine
# from .fred_engine import FredEngine
# from .polygon_engine import PolygonEngine
# from .openfigi import OpenFigiEngine

# Search engines
# from .duckduckgo_engine import DuckDuckGoEngine
# from .bing import BingEngine
# from .serper import SerperEngine
# from .searxng import SearxNGEngine

# News engines
# from .apitube import APITubeEngine
# from .rss_feed_manager import RSSFeedManager

# SEC engines
# from .sec_engine import SECEngine

# Code repository engines
# from .github_analyzer import GitHubAnalyzer
# from .pypi_search import PyPISearch

__all__ = [
    'BaseEngine',
    'SearchEngine',
    'MotherDuckEngine',
    # 'FMPEngine',
    # 'YahooFinanceEngine',
    # 'FredEngine',
    # 'PolygonEngine',
    # 'OpenFigiEngine',
    # 'DuckDuckGoEngine',
    # 'BingEngine',
    # 'SerperEngine',
    # 'SearxNGEngine',
    # 'APITubeEngine',
    # 'RSSFeedManager',
    # 'SECEngine',
    # 'GitHubAnalyzer',
    # 'PyPISearch',
] 