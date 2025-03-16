from django.urls import path

from .api import api

urlpatterns = [
    path("api/syzygy/", api.urls),
]
