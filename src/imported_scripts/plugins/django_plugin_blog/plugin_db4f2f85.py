import logging

import djp
from django.conf import settings
from django.urls import URLPattern, path

from .views import BlogFeed, archive, entry, index, tag, year

logger = logging.getLogger(__name__)


def get_blog_url_prefix() -> str:
    """Gets the blog URL prefix from settings or defaults to 'blog'."""
    return getattr(settings, "DJANGO_PLUGIN_BLOG_URL_PREFIX", "blog")


def generate_blog_url_patterns(blog_prefix: str) -> list[URLPattern]:
    """Generates URL patterns for the blog application."""
    patterns: list[URLPattern] = [
        path(f"{blog_prefix}/", index, name="django_plugin_blog_index"),
        path(
            f"{blog_prefix}/<int:year>/<slug:slug>/",
            entry,
            name="django_plugin_blog_entry",
        ),
        path(f"{blog_prefix}/archive/", archive, name="django_plugin_blog_archive"),
        path(f"{blog_prefix}/<int:year>/", year, name="django_plugin_blog_year"),
        path(f"{blog_prefix}/tag/<slug:slug>/", tag, name="django_plugin_blog_tag"),
        path(f"{blog_prefix}/feed/", BlogFeed(), name="django_plugin_blog_feed"),
    ]
    logger.info(f"DJP: Returning URL patterns: {patterns}")
    return patterns


@djp.hookimpl
def installed_apps() -> list[str]:
    """DJP hook implementation to add 'plugins.django_plugin_blog' to installed apps.

    Returns
    -------
        A list containing the string 'plugins.django_plugin_blog'.

    """
    logger.info("DJP: installed_apps hook called")
    return ["plugins.django_plugin_blog"]


@djp.hookimpl
def urlpatterns() -> list[URLPattern]:
    """DJP hook implementation to provide URL patterns for the blog application.

    Returns
    -------
        A list of URL patterns for the blog application.

    """
    logger.info("DJP: urlpatterns hook called")
    blog_prefix = get_blog_url_prefix()
    return generate_blog_url_patterns(blog_prefix)
