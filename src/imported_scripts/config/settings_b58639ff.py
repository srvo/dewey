INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ninja",  # Django Ninja for API
    "syzygy",  # Our app
]

# Django Ninja settings
NINJA_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# API Documentation settings
API_TITLE = "Syzygy API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "API for managing contacts, tasks, and enrichment workflows"
