import pytest
from celery.result import EagerResult
from ec1c.users.tasks import get_users_count
from ec1c.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_count(settings) -> None:
    """A basic test to execute the get_users_count Celery task."""
    batch_size = 3
    UserFactory.create_batch(batch_size)
    settings.CELERY_TASK_ALWAYS_EAGER = True
    task_result = get_users_count.delay()
    assert isinstance(task_result, EagerResult)
    assert task_result.result == batch_size
