import os


DATA_DIR = "data"


def create_directory_if_not_exists(directory_path: str) -> None:
    """Creates a directory if it does not already exist.

    Args:
        directory_path: The path to the directory.
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def get_data_file_path(filename: str) -> str:
    """Constructs the full path to a data file.

    Args:
        filename: The name of the data file.

    Returns:
        The full path to the data file.
    """
    create_directory_if_not_exists(DATA_DIR)
    return os.path.join(DATA_DIR, filename)