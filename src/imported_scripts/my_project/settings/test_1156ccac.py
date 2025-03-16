"""Test settings for pytest."""

from .settings import *  # noqa

# Use in-memory SQLite database for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Disable migrations during tests
MIGRATION_MODULES = {
    "auth": None,
    "contenttypes": None,
    "default": None,
    "sessions": None,
    "email_processing": None,
    "database": None,
    "syzygy": None,
}

# Disable celery tasks during tests
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Disable rate limiting during tests
RATE_LIMIT_ENABLED = False

# Use console email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
