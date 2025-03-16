from django.urls import path

from . import views
from .feeds import BlogFeed  # Assuming BlogFeed is in feeds.py

app_name = "blog"


def blog_patterns() -> list:
    """Define the URL patterns for the blog application.

    Returns:
        list: A list of URL patterns.

    """
    return [
        path("", views.index, name="index"),
        path("<int:year>/<slug:slug>/", views.entry, name="entry"),
        path("archive/", views.archive, name="archive"),
        path("<int:year>/", views.year, name="year"),
        path("tag/<slug:slug>/", views.tag, name="tag"),
        path("feed/", BlogFeed(), name="feed"),
    ]


urlpatterns = blog_patterns()
