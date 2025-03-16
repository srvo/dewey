"""ECIC Terminal Setup."""

from setuptools import find_packages, setup

setup(
    name="ecic",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9,<3.14",
    install_requires=[
        "textual>=0.40.0,<0.85.0",
        "ephem>=4.1.4",
        "sqlalchemy>=2.0.0",
        "asyncpg>=0.29.0",
        "alembic>=1.13.0",
        "psycopg2-binary>=2.9.9",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "yfinance>=0.2.36",
        "feedparser>=6.0.10",
        "aiohttp>=3.9.1",
        "pandas>=2.1.4",
        "asyncssh>=2.14.0",
        "psutil>=5.9.6",
        "markdown-it-py>=3.0.0",
        "icalendar>=5.0.11",
        "rich>=13.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
        ],
        "tools": [
            "visidata>=2.11.0",  # Data exploration
            "harlequin>=1.1.0",  # SQL client
            "gtop>=1.1.0",  # System monitoring
            "wtfutil>=0.43.0",  # Terminal dashboard
            "frogmouth>=0.7.0",  # Markdown viewer
            "calcure>=0.3.0",  # Calendar tool
        ],
    },
    entry_points={
        "console_scripts": [
            "ecic=ecic.cli:main",
        ],
    },
)
