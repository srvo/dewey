```python
import os
import sys


def print_python_info() -> None:
  """Prints Python executable, version, PATH, and virtual environment information."""
  print_executable()
  print_version()
  print_path()
  print_virtual_env()


def print_executable() -> None:
  """Prints the Python executable path."""
  print("Python executable:", sys.executable)


def print_version() -> None:
  """Prints the Python version."""
  print("Python version:", sys.version)


def print_path() -> None:
  """Prints the PATH environment variable."""
  print("PATH:", os.environ.get("PATH"))


def print_virtual_env() -> None:
  """Prints the VIRTUAL_ENV environment variable."""
  print("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV"))


if __name__ == "__main__":
  print_python_info()
```
