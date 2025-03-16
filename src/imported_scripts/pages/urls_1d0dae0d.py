from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("pages/", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("pages/<slug:slug>/", views.page_detail, name="page"),
]
