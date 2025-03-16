```python
import os
from typing import List, Optional, Union, Tuple


def process_files(
    root_dir: str,
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    include_hidden: bool = False,
    min_size_kb: Optional[float] = None,
    max_size_kb: Optional[float] = None,
) -> List[Tuple[str, int]]:
    """
    Recursively processes files within a directory, applying filtering based on
    file extension, directory exclusion, visibility, and file size.

    Args:
        root_dir: The root directory to start the file processing from.
        extensions: A list of file extensions to include (e.g., ['.txt', '.py']).
            If None, all file extensions are included.
        exclude_dirs: A list of directory names to exclude from processing.
            If None, no directories are excluded.
        include_hidden: Whether to include hidden files and directories (starting with '.').
            Defaults to False.
        min_size_kb: The minimum file size in kilobytes to include. If None, no minimum size is enforced.
        max_size_kb: The maximum file size in kilobytes to include. If None, no maximum size is enforced.

    Returns:
        A list of tuples, where each tuple contains the absolute path of a processed file
        and its size in bytes.  Returns an empty list if the root directory does not exist.

    Raises:
        TypeError: If any of the arguments are of the wrong type.
        ValueError: If min_size_kb is greater than max_size_kb.

    Examples:
        >>> process_files('my_directory', extensions=['.txt'])
        [('/path/to/my_directory/file1.txt', 1024), ('/path/to/my_directory/subdir/file2.txt', 2048)]

        >>> process_files('my_directory', exclude_dirs=['subdir'])
        [('/path/to/my_directory/file1.txt', 1024)]

        >>> process_files('my_directory', include_hidden=True)
        [('/path/to/my_directory/.hidden_file.txt', 512), ('/path/to/my_directory/file1.txt', 1024)]

        >>> process_files('my_directory', min_size_kb=1, max_size_kb=2)
        [('/path/to/my_directory/file1.txt', 1024), ('/path/to/my_directory/subdir/file2.txt', 2048)]
    """

    if not isinstance(root_dir, str):
        raise TypeError("root_dir must be a string.")
    if extensions is not None and not isinstance(extensions, list):
        raise TypeError("extensions must be a list of strings or None.")
    if exclude_dirs is not None and not isinstance(exclude_dirs, list):
        raise TypeError("exclude_dirs must be a list of strings or None.")
    if not isinstance(include_hidden, bool):
        raise TypeError("include_hidden must be a boolean.")
    if min_size_kb is not None and not isinstance(min_size_kb, (int, float)):
        raise TypeError("min_size_kb must be a number or None.")
    if max_size_kb is not None and not isinstance(max_size_kb, (int, float)):
        raise TypeError("max_size_kb must be a number or None.")

    if min_size_kb is not None and max_size_kb is not None and min_size_kb > max_size_kb:
        raise ValueError("min_size_kb cannot be greater than max_size_kb.")

    if not os.path.exists(root_dir):
        return []

    results: List[Tuple[str, int]] = []

    for root, dirs, files in os.walk(root_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if (exclude_dirs is None or d not in exclude_dirs) and (include_hidden or not d.startswith('.'))]

        for file in files:
            if not include_hidden and file.startswith('.'):
                continue

            if extensions is not None and not any(file.endswith(ext) for ext in extensions):
                continue

            file_path = os.path.join(root, file)
            file_size_bytes = os.path.getsize(file_path)
            file_size_kb = file_size_bytes / 1024.0

            if min_size_kb is not None and file_size_kb < min_size_kb:
                continue

            if max_size_kb is not None and file_size_kb > max_size_kb:
                continue

            results.append((os.path.abspath(file_path), file_size_bytes))

    return results
```