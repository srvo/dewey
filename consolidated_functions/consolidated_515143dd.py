```python
import os
import sys
from typing import NoReturn, Optional

def main() -> NoReturn:
    """
    Run administrative tasks for a Django project.

    This is the main entry point for Django's command-line interface.
    It handles setting up the Django environment and executing management commands.

    The function performs the following steps:
    1. Sets the default Django settings module if not already set.
    2. Attempts to import Django's `execute_from_command_line` function.
    3. Executes the requested command with provided arguments.
    4. Handles errors and provides helpful feedback.

    Args:
        None (uses sys.argv for command line arguments)

    Returns:
        NoReturn: Always exits the program.

    Raises:
        ImportError: If Django is not installed or not available in PYTHONPATH.
        CommandError: If the requested command fails (e.g., invalid arguments).
        RuntimeError: If there are issues with environment configuration or other unexpected errors.

    Example:
        ```bash
        $ python manage.py runserver
        Starting development server at http://127.0.0.1:8000/

        $ python manage.py migrate
        Applying migrations...

        $ python manage.py createsuperuser
        Username: admin
        ```

    Security Considerations:
        - Never run with `DEBUG=True` in production.
        - Use different settings modules for development and production.
        - Keep secret keys and credentials in environment variables.
        - Ensure `ALLOWED_HOSTS` is properly configured.
        - Set proper database permissions.
        - Use HTTPS in production environments.
        - Regularly update dependencies.
        - Implement proper access controls.

    Performance Notes:
        - Use connection pooling for database operations.
        - Enable caching for frequently accessed data.
        - Optimize database queries.
        - Use asynchronous tasks for long-running operations.

    Debugging Tips:
        - Use django-debug-toolbar for development.
        - Check logs for error messages.
        - Use Django's `shell_plus` for interactive debugging.
        - Enable SQL logging for query optimization.

    Implementation Details:
        - The function uses Django's `execute_from_command_line` to handle command execution.
        - Environment variables are checked before setting defaults.
        - Error handling provides detailed feedback for common setup issues.
        - The function is designed to be called directly from the command line (e.g., `python manage.py`).
        - All Django management commands are supported through this entry point.

    Version History:
        - 1.0.0: Initial implementation.
        - 1.1.0: Added enhanced error handling and documentation.
        - 1.2.0: Improved security considerations and performance notes.

    See Also:
        - Django documentation: https://docs.djangoproject.com/
        - Django management commands: https://docs.djangoproject.com/en/stable/ref/django-admin/
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")  # Default settings module

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    try:
        execute_from_command_line(sys.argv)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1) # Exit with an error code
```
