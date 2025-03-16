from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Says hello"

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.SUCCESS("Hello from custom command!"))
