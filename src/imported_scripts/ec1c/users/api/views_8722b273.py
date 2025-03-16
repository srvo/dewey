from typing import TYPE_CHECKING

from ec1c.users.models import User
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .serializers import UserSerializer

if TYPE_CHECKING:
    from rest_framework.serializers import Serializer


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    """ViewSet for managing User objects.
    Provides retrieve, list, and update operations.
    """

    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        """Filters the queryset to return only the current user's data."""
        return self._filter_queryset_by_user_id()

    def _filter_queryset_by_user_id(self):
        """Filters the queryset based on the current user's ID.

        Returns:
            QuerySet: A filtered queryset containing only the current user's data.

        """
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        """Endpoint to retrieve the current user's information.

        Returns:
            Response: A response containing the serialized user data.

        """
        return self._get_user_data(request)

    def _get_user_data(self, request) -> Response:
        """Serializes and returns the current user's data.

        Args:
            request: The request object.

        Returns:
            Response: A response containing the serialized user data.

        """
        serializer: Serializer = UserSerializer(
            request.user,
            context={"request": request},
        )
        return Response(status=status.HTTP_200_OK, data=serializer.data)
