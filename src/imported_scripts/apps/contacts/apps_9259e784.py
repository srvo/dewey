from django.apps import AppConfig


class ContactsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contacts"

    def ready(self) -> None:
        try:
            # Only import signals if integrations app is installed
            from integrations import signals  # noqa
        except ImportError:
            pass  # Integrations app not installed


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations"

    def ready(self) -> None:
        try:
            import integrations.signals  # noqa
        except ImportError:
            pass
