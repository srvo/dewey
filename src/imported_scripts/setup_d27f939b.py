from setuptools import find_packages, setup

setup(
    name="ecic",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "textual>=0.40.0,<0.85.0",
        "sqlalchemy",
        "asyncio",
        "pyyaml",
        "asyncpg",
    ],
    entry_points={
        "console_scripts": [
            "ecic=ecic.cli:main",
        ],
    },
)
