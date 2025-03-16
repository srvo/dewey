from setuptools import find_packages, setup


def configure_package() -> dict:
    """Configures the package metadata.

    Returns
    -------
        A dictionary containing the setup configuration.

    """
    return {
        "name": "ledger_tools",
        "version": "0.1",
        "packages": find_packages(
            include=["bin", "classification_engine", "journal_writer"],
        ),
        "package_dir": {
            "bin": "bin",
            "classification_engine": ".",
            "journal_writer": ".",
        },
        "install_requires": [
            "python-dateutil",
            "requests",
            "pydantic",
            "pyyaml",
        ],
        "entry_points": {
            "console_scripts": [
                "process_feedback=bin.process_feedback:main",
            ],
        },
    }


if __name__ == "__main__":
    setup(**configure_package())
