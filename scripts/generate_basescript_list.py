import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/srvo/dewey")
OUTPUT_FILE = PROJECT_ROOT / "incomplete_basescript_files.txt"


def find_incomplete_files():
    """Function find_incomplete_files."""
    files = []
    for py_file in PROJECT_ROOT.rglob("*.py"):
        if py_file.name == "generate_basescript_list.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            if "from dewey.core.base_script import BaseScript" in content:
                if not re.search(r"class \w+\(BaseScript\):", content):
                    files.append(str(py_file.relative_to(PROJECT_ROOT)))
        except Exception as e:
            print(f"Skipping {py_file}: {str(e)}")

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(files))


if __name__ == "__main__":
    find_incomplete_files()
    print(f"File list generated at {OUTPUT_FILE}")
