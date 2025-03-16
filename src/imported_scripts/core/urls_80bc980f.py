"""Core URL Configuration.

This module defines the URL routing for the entire Django application. It serves as the central
point for all URL patterns, including:

- Admin interface
- Authentication (allauth)
- API endpoints
- Core pages
- Blog functionality
- Media handling
- Debug toolbar (development only)

The URL patterns follow Django's URL routing best practices, with clear separation between:
- Core application routes
- Third-party integrations
- API endpoints
- Development tools

URL patterns are organized by functionality and include detailed comments explaining each route.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from syzygy.api import api as syzygy_api

from .api import api as core_api
from .views import health_check


def redirect_to_admin(request):
    """Redirect root URL to Django admin interface.

    Args:
    ----
        request: HttpRequest object

    Returns:
    -------
        HttpResponseRedirect: Redirect response to admin index page

    """
    return redirect("admin:index")


# Base URL patterns for the application
urlpatterns = [
    # Root URL redirects to admin interface
    path("", redirect_to_admin, name="home"),
    # Django admin interface
    path("admin/", admin.site.urls),
    # Allauth authentication URLs (login, logout, signup, etc)
    path("accounts/", include("allauth.urls")),
    # Core API endpoints
    path("api/", core_api.urls),
    # Syzygy API endpoints (AI/ML functionality)
    path("api/syzygy/", syzygy_api.urls),
    # Core pages (static content, about, etc)
    path("", include("core.pages.urls")),
    # Blog functionality
    path("blog/", include("blog.urls")),
    # MarkdownX editor URLs
    path("markdownx/", include("markdownx.urls")),
    # Health check endpoint
    path("health/", health_check, name="health_check"),
]

# Development-only URL patterns
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = (
        [
            # Debug toolbar URLs
            path("__debug__/", include(debug_toolbar.urls)),
        ]
        + urlpatterns
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )  # Serve media files in development
