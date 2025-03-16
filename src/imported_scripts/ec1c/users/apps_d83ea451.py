import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "ec1c.users"
    verbose_name = _("Users")

    def ready(self) -> None:
        with contextlib.suppress(ImportError):
            import ec1c.users.signals  # noqa: F401
