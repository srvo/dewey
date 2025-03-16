from ec1c.users.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer[User]):
    """Serializer for the User model."""

    class Meta:
        """Meta class for UserSerializer."""

        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }
