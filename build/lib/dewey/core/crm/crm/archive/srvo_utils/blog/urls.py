from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:year>/<slug:slug>/", views.entry, name="entry"),
    path("archive/", views.archive, name="archive"),
    path("<int:year>/", views.year, name="year"),
    path("tag/<slug:slug>/", views.tag, name="tag"),
    path("feed/", views.BlogFeed(), name="feed"),
]
