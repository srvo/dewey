```python
from setuptools import find_packages, setup


def get_install_requires() -> list[str]:
    """Returns the list of required packages."""
    return [
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
    ]


def setup_package() -> None:
    """Sets up the package."""
    setup(
        name="ethifinx",
        version="0.1.0",
        packages=find_packages(include=["ethifinx", "ethifinx.*"]),
        install_requires=get_install_requires(),
        python_requires=">=3.11",
    )


if __name__ == "__main__":
    setup_package()
```
