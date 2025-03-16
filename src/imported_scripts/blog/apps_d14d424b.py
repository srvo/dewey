from django.apps import AppConfig


class BlogConfig(AppConfig):
    """Configuration class for the 'blog' app."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "blog"
