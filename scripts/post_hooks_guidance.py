#!/usr/bin/env python3
"""
Post-hooks guidance script for pre-commit.

This script provides clear, colorful guidance after pre-commit hooks run,
showing which files were modified and what actions to take next.
It offers an interactive menu to perform common post-hook actions,
including staging changes and using aider to fix issues.
"""

import os
import re
import subprocess
import sys


def get_modified_files() -> list[str]:
    """Get list of modified files that need to be staged."""
    try:
        # Get modified files that aren't staged
        result = subprocess.run(
            ["git", "diff", "--name-only"], capture_output=True, text=True, check=True,
        )
        modified = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Get staged files with modifications
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            check=True,
        )
        staged = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Return only files that are modified but not staged
        return [f for f in modified if f and f not in staged]
    except subprocess.CalledProcessError:
        return []


def get_hook_errors() -> dict[str, str]:
    """
    Gather any error messages from pre-commit hooks output.

    Returns a dictionary of {filename: error_message}
    """
    errors = {}

    # Check if stdout was redirected to a file
    if not sys.stdin.isatty():
        hook_output = sys.stdin.read()

        # Simple parsing strategy - find files and their errors
        # This is basic and might need improvement for different hook outputs
        file_error_pattern = re.compile(
            r"([^\s]+\.[^\s]+).*?\n(.*?)(?=\n[^\s]+\.[^\s]+|\Z)", re.DOTALL,
        )
        matches = file_error_pattern.findall(hook_output)

        for file_path, error_msg in matches:
            if error_msg and "Failed" in error_msg:
                errors[file_path] = error_msg.strip()

    return errors


def parse_pre_commit_output() -> tuple[dict[str, list[str]], list[str], list[str]]:
    """
    Parse pre-commit output to get better context on hooks and modifications.

    Returns
    -------
        Tuple containing:
        - Dictionary of {hook_name: list_of_modified_files}
        - List of hooks that failed but didn't modify files
        - List of syntax errors detected

    """
    hook_results = {}
    failed_hooks = []
    syntax_errors = []

    # Check if stdin has content (redirected from pre-commit)
    if not sys.stdin.isatty():
        try:
            hook_output = sys.stdin.read()

            # Pattern to match hook name and status
            hook_pattern = re.compile(r"([^\n.]+)\.+(\w+)")

            # Pattern to match "Fixing" lines that come after hook failures
            fixing_pattern = re.compile(r"Fixing\s+([^\n]+)")

            # Pattern to match syntax errors
            syntax_error_pattern = re.compile(
                r"(?:error: |Syntax error in )([^:]+):[^:]+: (Expected an indented block|[^\n]+)",
            )

            current_hook = None

            for line in hook_output.split("\n"):
                # Check for syntax errors
                syntax_match = syntax_error_pattern.search(line)
                if syntax_match:
                    file_path = syntax_match.group(1).strip()
                    error_msg = syntax_match.group(2).strip()
                    syntax_errors.append(f"{file_path}: {error_msg}")

                # Check if line describes a hook and its status
                hook_match = hook_pattern.search(line)
                if hook_match:
                    hook_name = hook_match.group(1).strip()
                    status = hook_match.group(2).strip()
                    current_hook = hook_name

                    # Initialize the hook's entry in the dictionary
                    if current_hook not in hook_results:
                        hook_results[current_hook] = []

                    # If hook failed but didn't modify files
                    if status == "Failed" and "files were modified" not in line:
                        failed_hooks.append(current_hook)

                # Check if line indicates a file fix
                fixing_match = fixing_pattern.search(line)
                if fixing_match and current_hook is not None:
                    fixed_file = fixing_match.group(1).strip()
                    hook_results[current_hook].append(fixed_file)
        except Exception as e:
            print(colorize(f"Error parsing pre-commit output: {e}", "1;31"))

    # If we're running interactively (not from pre-commit), get info from git status
    if not hook_results and sys.stdin.isatty():
        try:
            # Get list of modified files from git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                # Create a fallback hook result with all modified files
                hook_results["Interactive Run"] = []

                for line in result.stdout.split("\n"):
                    if line.strip():
                        # Git status output format is "XY filename"
                        # where X is staging status and Y is working tree status
                        status = line[:2]
                        file_path = line[3:].strip()

                        # Add files that are modified but not staged (M in second column)
                        if status[1] in ["M", "?", "A", "D"]:
                            hook_results["Interactive Run"].append(file_path)
        except Exception as e:
            print(colorize(f"Error getting modified files from git: {e}", "1;31"))

    return hook_results, failed_hooks, syntax_errors


def colorize(text: str, color_code: str) -> str:
    """Add color to text."""
    return f"\033[{color_code}m{text}\033[0m"


def stage_files(files: list[str]) -> bool:
    """
    Stage modified files with git add.

    Returns True if successful, False otherwise.
    """
    if not files:
        print(colorize("No files to stage.", "1;33"))
        return False

    try:
        # Use chunking for large file lists to avoid command line length limitations
        # Process in batches of 50 files
        chunk_size = 50
        success = True

        if len(files) > chunk_size:
            print(
                colorize(
                    f"Staging {len(files)} files in chunks of {chunk_size}...", "1;33",
                ),
            )

            # Process in chunks
            for i in range(0, len(files), chunk_size):
                chunk = files[i : i + chunk_size]
                try:
                    subprocess.run(["git", "add"] + chunk, check=True)
                    print(
                        colorize(
                            f"Staged files {i + 1}-{min(i + chunk_size, len(files))} of {len(files)}",
                            "1;32",
                        ),
                    )
                except subprocess.CalledProcessError as e:
                    print(
                        colorize(
                            f"Error staging chunk {i // chunk_size + 1}: {e}", "1;31",
                        ),
                    )
                    success = False
        else:
            # Small enough list to process at once
            subprocess.run(["git", "add"] + files, check=True)

        if success:
            print(colorize(f"Successfully staged {len(files)} files.", "1;32"))
        return success
    except subprocess.CalledProcessError as e:
        print(colorize(f"Error staging files: {e}", "1;31"))

        # Offer alternative
        print(colorize("\nTry using the following command instead:", "1;33"))
        print("  git add .")
        return False


def run_aider_with_fallback(file_path: str, error_message: str) -> None:
    """
    Run aider on a file with error message as context.
    Fall back to simple git add if aider is not available.
    """
    try:
        # Enhance the prompt to focus on syntax errors if that seems to be the issue
        if (
            "Expected an indented block" in error_message
            or "Syntax error" in error_message
        ):
            prompt = f"Fix the following syntax error in this file: {error_message}. Add the missing indented block or correct the syntax error."
        else:
            prompt = (
                f"Fix the following pre-commit hook error in this file: {error_message}"
            )

        # Check if CONVENTIONS.md exists
        conventions_path = "CONVENTIONS.md"
        includes_conventions = os.path.exists(conventions_path)

        # Check if aider is available
        try:
            subprocess.run(["which", "aider"], check=True, capture_output=True)
            aider_available = True
        except subprocess.CalledProcessError:
            aider_available = False

        if not aider_available:
            print(colorize("\nAider not found in your PATH.", "1;31"))
            print(colorize("You can install it with: pip install aider-chat", "1;33"))
            print(
                colorize(
                    "\nWould you like to open the file in your default editor instead?",
                    "1;33",
                ),
            )

            if input(colorize("Open in editor? (y/n): ", "1;33")).lower() == "y":
                # Try to open in default editor
                try:
                    if sys.platform == "darwin":  # macOS
                        subprocess.run(["open", file_path], check=True)
                    elif sys.platform == "win32":  # Windows
                        subprocess.run(["start", file_path], check=True, shell=True)
                    else:  # Linux and others
                        subprocess.run(["xdg-open", file_path], check=True)
                    print(
                        colorize(
                            f"\nOpened {file_path} in your default editor.", "1;32",
                        ),
                    )
                except Exception as e:
                    print(colorize(f"Error opening file: {e}", "1;31"))
            return

        # Print what we're about to do
        print(colorize(f"Running aider to fix issues in {file_path}...", "1;34"))
        if includes_conventions:
            print(colorize("Including CONVENTIONS.md as reference context", "1;34"))
        print(colorize(f"Prompt: {prompt}", "1;36"))

        # Confirm before proceeding
        if input(colorize("Proceed? (y/n): ", "1;33")).lower() != "y":
            print(colorize("Cancelled aider command.", "1;33"))
            return

        # Prepare command with or without conventions file
        if includes_conventions:
            subprocess.run(
                ["aider", "--message", prompt, conventions_path, file_path], check=True,
            )
        else:
            subprocess.run(["aider", "--message", prompt, file_path], check=True)

    except subprocess.CalledProcessError as e:
        print(colorize(f"Error running aider: {e}", "1;31"))
    except FileNotFoundError:
        print(
            colorize(
                "The aider command was not found. Please install aider: pip install aider-chat",
                "1;31",
            ),
        )


def select_file_menu(files: list[str], action: str) -> str | None:
    """Show a menu to select a file from a list."""
    if not files:
        print(colorize("No files available.", "1;33"))
        return None

    # Check if we're in an interactive terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(colorize("Cannot show interactive menu in non-interactive mode.", "1;31"))
        return None

    print(colorize(f"\nSelect a file to {action}:", "1;36"))
    for i, file in enumerate(files, 1):
        print(f"  {i}. {file}")
    print("  0. Return to main menu")

    try:
        while True:
            choice = input(colorize("Enter number: ", "1;33"))

            try:
                choice_num = int(choice)
                if choice_num == 0:
                    return None
                if 1 <= choice_num <= len(files):
                    return files[choice_num - 1]
                print(colorize("Invalid selection. Try again.", "1;31"))
            except ValueError:
                print(colorize("Please enter a number.", "1;31"))
    except EOFError:
        print(
            colorize(
                "Cannot read input. Run this script directly for interactive mode.",
                "1;31",
            ),
        )
        return None


def display_hook_summary(hook_results: dict[str, list[str]]) -> None:
    """Display a summary of what each hook did."""
    print(colorize("\n=== HOOK SUMMARY ===", "1;36"))

    if not hook_results:
        print(colorize("No hook information available.", "1;33"))
        print(colorize("Run this script directly after pre-commit with: ", "1;33"))
        print(
            colorize("  pre-commit run | python scripts/post_hooks_guidance.py", "1;36"),
        )
        return

    for hook, files in hook_results.items():
        if files:
            file_count = len(files)
            print(
                colorize(f"\n{hook}: ", "1;33")
                + colorize(f"Modified {file_count} files", "1;32"),
            )

            # Show a preview of files (up to 5)
            preview_files = files[:5]
            for file in preview_files:
                print(f"  - {file}")

            # Indicate if there are more files
            if file_count > 5:
                print(colorize(f"  ... and {file_count - 5} more files", "1;33"))
        else:
            print(
                colorize(f"\n{hook}: ", "1;33") + colorize("No files modified", "1;31"),
            )


def display_syntax_errors(syntax_errors: list[str]) -> None:
    """Display syntax errors found in files."""
    if not syntax_errors:
        return

    print(colorize("\n=== SYNTAX ERRORS ===", "1;31"))
    print(
        colorize(
            "The following files have syntax errors that need to be fixed:", "1;37",
        ),
    )

    for i, error in enumerate(syntax_errors, 1):
        print(f"  {i}. {error}")

    print(colorize("\nThese errors must be fixed before committing.", "1;37"))
    print(colorize("Consider using 'aider' to fix these files:", "1;36"))
    print("  python scripts/post_hooks_guidance.py")
    print("  Then select option 3 to fix the files with syntax errors")


def show_modified_files_menu() -> None:
    """Interactive menu option to show all modified files."""
    modified_files = get_modified_files()

    if not modified_files:
        print(colorize("\nNo modified files found.", "1;33"))
        return

    print(colorize("\nModified files:", "1;33"))

    # Show files with numbers for easier reference
    for i, file in enumerate(modified_files, 1):
        print(f"  {i:3d}. {file}")

    print(colorize(f"\nTotal: {len(modified_files)} files", "1;36"))

    # Ask if user wants to stage some of these files
    if sys.stdin.isatty() and sys.stdout.isatty():
        choice = input(colorize("\nStage these files? (y/n): ", "1;33")).lower()
        if choice == "y":
            stage_files(modified_files)


def show_interactive_menu(
    modified_files: list[str],
    errors: dict[str, str],
    hook_results: dict[str, list[str]],
    failed_hooks: list[str],
    syntax_errors: list[str],
) -> None:
    """Show an interactive menu of actions the user can take."""
    # Check if we're in an interactive terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(
            colorize("\nRun this script directly to see the interactive menu:", "1;36"),
        )
        print(f"  python {os.path.basename(__file__)}")
        return

    while True:
        print("\n" + colorize("=== POST-HOOKS ACTIONS ===", "1;36"))
        print("1. Stage all modified files")
        print("2. Stage a specific file")
        print("3. Use aider to fix a file with errors")
        print("4. Show modified files list")
        print("5. Show hook summary")
        print("6. Show syntax errors")
        print("7. Exit")

        try:
            choice = input(colorize("\nEnter your choice (1-7): ", "1;33"))

            if choice == "1":
                stage_files(modified_files)

            elif choice == "2":
                file = select_file_menu(modified_files, "stage")
                if file:
                    stage_files([file])

            elif choice == "3":
                # Get files with errors - prioritize syntax errors, then hook errors, then modified files
                error_files = []

                if syntax_errors:
                    for error in syntax_errors:
                        # Extract filename from error message
                        file_path = error.split(":", 1)[0].strip()
                        if os.path.exists(file_path) and file_path not in error_files:
                            error_files.append(file_path)

                if not error_files:
                    error_files = list(errors.keys())

                # If no error files from parsing, offer all modified files
                if not error_files:
                    error_files = modified_files

                file = select_file_menu(error_files, "fix with aider")
                if file:
                    # Check if this file has a syntax error
                    error_msg = ""
                    for err in syntax_errors:
                        if err.startswith(file + ":"):
                            error_msg = err
                            break

                    # If no syntax error found, use the hook error message if available
                    if not error_msg:
                        error_msg = errors.get(
                            file, "Fix any code quality issues in this file",
                        )

                    run_aider_with_fallback(file, error_msg)

            elif choice == "4":
                show_modified_files_menu()

            elif choice == "5":
                display_hook_summary(hook_results)

                if failed_hooks:
                    print(
                        colorize(
                            "\nThe following hooks failed without modifying files:",
                            "1;31",
                        ),
                    )
                    for hook in failed_hooks:
                        print(f"  - {hook}")

            elif choice == "6":
                display_syntax_errors(syntax_errors)

            elif choice == "7":
                print(colorize("\nExiting. Good luck with your commit!", "1;32"))
                break

            else:
                print(
                    colorize(
                        "\nInvalid choice. Please enter a number between 1 and 7.",
                        "1;31",
                    ),
                )
        except EOFError:
            # Handle the case where we can't read from stdin
            print(
                colorize(
                    "\nCannot read input. Run this script directly for interactive mode.",
                    "1;31",
                ),
            )
            break


def print_guidance():
    """Print helpful guidance on next steps after hooks run."""
    modified_files = get_modified_files()
    errors = get_hook_errors()
    hook_results, failed_hooks, syntax_errors = parse_pre_commit_output()

    print("\n" + colorize("=== NEXT STEPS GUIDANCE ===", "1;36"))

    # Check for syntax errors first as they're critical
    if syntax_errors:
        print(
            colorize("\nCRITICAL: ", "1;31")
            + colorize(
                f"Found {len(syntax_errors)} syntax errors that must be fixed before committing!",
                "1;37",
            ),
        )
        print(
            colorize(
                "These are usually due to missing indentation blocks in Python files.",
                "1;37",
            ),
        )

        # Show just a few examples
        for error in syntax_errors[:3]:
            print(colorize(f"  - {error}", "1;31"))

        if len(syntax_errors) > 3:
            print(colorize(f"  ... and {len(syntax_errors) - 3} more errors", "1;31"))

        print(colorize("\nRun this script interactively to fix these errors:", "1;36"))
        print(f"  python {os.path.basename(__file__)}")

    # Explain the "Failed" status that actually fixed files
    if hook_results:
        hooks_that_fixed = [hook for hook, files in hook_results.items() if files]
        if hooks_that_fixed:
            print(
                colorize("\nIMPORTANT: ", "1;31")
                + colorize(
                    "Some hooks reported as 'Failed' actually FIXED issues in your files.",
                    "1;37",
                ),
            )
            print(
                colorize(
                    "This is normal - it means pre-commit automatically corrected problems for you.",
                    "1;37",
                ),
            )
            print(
                colorize(
                    "You need to STAGE these changes before you can commit.", "1;37",
                ),
            )

    if modified_files:
        print(
            "\n"
            + colorize(f"{len(modified_files)} files were modified by hooks:", "1;33"),
        )
        # Show at most 5 files to avoid overwhelming output
        preview_files = modified_files[:5]
        for file in preview_files:
            print(f"  - {file}")

        # Indicate if there are more files
        if len(modified_files) > 5:
            print(colorize(f"  ... and {len(modified_files) - 5} more files", "1;33"))

        # In non-interactive mode, show git command help
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            # For large file lists, suggest using git add .
            if len(modified_files) > 10:
                print("\n" + colorize("To stage all modified files:", "1;32"))
                print("  git add .")
            else:
                files_str = " ".join(modified_files)
                print(
                    "\n"
                    + colorize(
                        "Run these commands to stage changes and commit:", "1;32",
                    ),
                )
                print(f"  git add {files_str}")

            print('  git commit -m "Your message"')
            print(
                "\n"
                + colorize(
                    "Or run this script directly for interactive options:", "1;36",
                ),
            )
            print(f"  python {os.path.basename(__file__)}")

        # Only show interactive menu if in interactive mode
        show_interactive_menu(
            modified_files, errors, hook_results, failed_hooks, syntax_errors,
        )
    else:
        print(
            "\n"
            + colorize("No files were modified by hooks that need staging.", "1;32"),
        )

        # Check if there were any hook failures or syntax errors
        if (
            failed_hooks
            or syntax_errors
            or any(arg.lower() == "failed" for arg in sys.argv)
        ):
            if not syntax_errors:  # Only show this if we don't have syntax errors (which are more critical)
                print(
                    "\n"
                    + colorize(
                        "However, some hooks failed. Fix the issues and try again.",
                        "1;31",
                    ),
                )

            # Show failing hook information
            if failed_hooks:
                print(colorize("\nFailing hooks:", "1;31"))
                for hook in failed_hooks:
                    print(f"  - {hook}")

            # Only show interactive menu if in interactive mode
            show_interactive_menu([], errors, hook_results, failed_hooks, syntax_errors)
        elif not syntax_errors:  # Only show this if there are no syntax errors
            print(
                "\n" + colorize("All hooks passed! Your commit should proceed.", "1;32"),
            )

    # Always exit with success in hook mode to not block commits
    # The actual exit code from pre-commit is handled separately
    print("\n" + colorize("==========================", "1;36") + "\n")


if __name__ == "__main__":
    # For hook execution, always exit with success code
    # so that we don't prevent the commit from proceeding
    try:
        print_guidance()
        sys.exit(0)
    except Exception as e:
        print(colorize(f"Error in post-hooks guidance: {e}", "1;31"))
        # Still exit with 0 when used as a hook
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            sys.exit(0)
        else:
            sys.exit(1)
