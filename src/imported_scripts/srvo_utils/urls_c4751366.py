"""URL Configuration for srvo_utils project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("syzygy.urls")),  # Include Syzygy URLs (includes API)
]
