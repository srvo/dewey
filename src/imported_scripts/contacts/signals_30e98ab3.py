from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import GoogleContact


@receiver(post_save, sender=GoogleContact)
def update_contact(sender, instance, created, **kwargs) -> None:
    """Signal handler to sync contact changes."""
    # Implement contact sync logic here
