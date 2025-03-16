"""WSGI Configuration.

This module contains the WSGI application configuration for the Django project.
It serves as the entry point for WSGI-compatible web servers to serve the application.

The WSGI configuration:
- Sets the default Django settings module
- Creates the WSGI application object
- Provides the interface for WSGI servers to communicate with Django

This file should typically not need modification unless you're using a custom
WSGI middleware or server configuration.
"""

import os

from django.core.wsgi import get_wsgi_application

# Set the default Django settings module for the 'wsgi' application.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Create the WSGI application object that will be used by the WSGI server
application = get_wsgi_application()
