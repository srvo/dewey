```python
import os
import re
from typing import List, Dict, Union, Optional, Tuple, Callable

def analyze_files(
    file_paths: Union[str, List[str]],
    file_content_analyzer: Optional[Callable[[str], Dict[str, Union[str, int, float, bool, None]]]] = None,
    file_extension_filter: Optional[Union[str, List[str]]] = None,
    recursive: bool = False,
    error_handling: str = "ignore",  # "ignore", "raise", "return_errors"
) -> Dict[str, Union[Dict[str, Union[str, int, float, bool, None]], str]]:
    """Analyzes files based on specified criteria and returns analysis results.

    This function provides a flexible way to analyze files, supporting single file,
    list of files, filtering by file extension, recursive directory traversal,
    and customizable file content analysis.  It also offers robust error handling.

    Args:
        file_paths:  A string representing a single file path, or a list of strings
            representing file paths or directory paths.  If a directory path is
            provided and `recursive` is True, all files within the directory and
            its subdirectories will be analyzed.
        file_content_analyzer: An optional callable (function) that takes a file path
            (string) as input and returns a dictionary containing analysis results.
            If not provided, the function will only collect file metadata (name, size, etc.).
            The dictionary's values can be of various types (string, int, float, bool, None).
        file_extension_filter: An optional string or list of strings representing file
            extensions to filter by (e.g., ".txt", [".py", ".txt"]).  If provided,
            only files with matching extensions will be analyzed.  The comparison is
            case-insensitive.
        recursive: A boolean indicating whether to recursively traverse directories
            when `file_paths` contains directory paths. Defaults to False.
        error_handling: A string specifying how to handle errors during file processing.
            Options are:
                - "ignore":  Ignores errors and continues processing other files.
                - "raise":  Raises the exception immediately.
                - "return_errors": Returns a dictionary where keys are file paths
                  and values are either analysis results (if successful) or error messages (if an error occurred).

    Returns:
        A dictionary where keys are file paths (strings) and values are either:
            - A dictionary containing the analysis results (if successful).  The
              structure of this dictionary depends on the `file_content_analyzer`.
            - An error message (if `error_handling` is "return_errors" and an error occurred).
            - If `file_paths` is a single file and no errors occur, returns a dictionary
              containing the analysis results for that single file.

    Raises:
        Exception: If `error_handling` is "raise" and an error occurs during file processing.
        TypeError: If `file_paths` is not a string or a list of strings.
        ValueError: If `error_handling` is not one of the allowed values.

    Examples:
        # Analyze a single file, collecting metadata only.
        results = analyze_files("my_file.txt")

        # Analyze multiple files, filtering by extension, and using a custom analyzer.
        def custom_analyzer(file_path: str) -> Dict[str, Union[str, int]]:
            with open(file_path, "r") as f:
                content = f.read()
                return {"line_count": len(content.splitlines()), "file_size": os.path.getsize(file_path)}
        results = analyze_files(["file1.py", "file2.txt", "dir/"], file_content_analyzer=custom_analyzer, file_extension_filter=[".py"], recursive=True)

        # Handle errors by returning error messages.
        results = analyze_files("nonexistent_file.txt", error_handling="return_errors")
    """

    if not isinstance(file_paths, (str, list)):
        raise TypeError("file_paths must be a string or a list of strings.")

    if error_handling not in ("ignore", "raise", "return_errors"):
        raise ValueError("error_handling must be 'ignore', 'raise', or 'return_errors'.")

    results: Dict[str, Union[Dict[str, Union[str, int, float, bool, None]], str]] = {}

    def analyze_single_file(file_path: str) -> Optional[Dict[str, Union[str, int, float, bool, None]]]:
        """Analyzes a single file and returns the results or None on error."""
        try:
            if not os.path.isfile(file_path):
                return None  # Skip if not a file

            if file_extension_filter:
                if isinstance(file_extension_filter, str):
                    extensions = [file_extension_filter.lower()]
                else:
                    extensions = [ext.lower() for ext in file_extension_filter]
                if not any(file_path.lower().endswith(ext) for ext in extensions):
                    return None  # Skip if extension doesn't match

            file_analysis: Dict[str, Union[str, int, float, bool, None]] = {
                "file_name": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "last_modified": os.path.getmtime(file_path),
            }

            if file_content_analyzer:
                try:
                    content_analysis = file_content_analyzer(file_path)
                    if content_analysis:  # Avoid merging None
                        file_analysis.update(content_analysis)
                except Exception as e:
                    if error_handling == "raise":
                        raise
                    elif error_handling == "return_errors":
                        return {"error": f"Error during content analysis: {str(e)}"}
                    else:  # error_handling == "ignore"
                        print(f"Warning: Error during content analysis for {file_path}: {str(e)}")

            return file_analysis

        except Exception as e:
            if error_handling == "raise":
                raise
            elif error_handling == "return_errors":
                return {"error": f"Error processing file: {str(e)}"}
            else:  # error_handling == "ignore"
                print(f"Warning: Error processing {file_path}: {str(e)}")
                return None

    if isinstance(file_paths, str):
        analysis_result = analyze_single_file(file_paths)
        if analysis_result:
            return {file_paths: analysis_result}
        else:
            return {}  # Return empty dict if file doesn't exist or is filtered out

    for file_path in file_paths:
        if not isinstance(file_path, str):
            if error_handling == "raise":
                raise TypeError("All elements in file_paths list must be strings.")
            elif error_handling == "return_errors":
                results[str(file_path)] = "Invalid file path: not a string"
                continue
            else:
                print(f"Warning: Invalid file path (not a string): {file_path}")
                continue

        if os.path.isfile(file_path):
            analysis_result = analyze_single_file(file_path)
            if analysis_result:
                results[file_path] = analysis_result
        elif os.path.isdir(file_path):
            if recursive:
                for root, _, files in os.walk(file_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        analysis_result = analyze_single_file(full_path)
                        if analysis_result:
                            results[full_path] = analysis_result
            else:
                # Handle directory without recursion
                pass  # Do nothing, as per the specification.  Could add a warning here.
        else:
            if error_handling == "return_errors":
                results[file_path] = "File or directory not found"
            elif error_handling != "ignore":
                print(f"Warning: File or directory not found: {file_path}")

    return results
```