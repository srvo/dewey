from setuptools import find_packages, setup

setup(
    name="ethifinx",
    version="0.1.0",
    packages=find_packages(include=["ethifinx", "ethifinx.*"]),
    install_requires=[
        "joblib",
        "duckdb",
        "pandas",
        "requests",
        "click",
        "pytest",
        "pytest-mock",
        "pytest-cov",
        "boto3",
        "duckduckgo-search",
        "ratelimit",
        "botocore",
        "duckdb-engine",
    ],
    python_requires=">=3.11",
)
