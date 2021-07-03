import pytest

from django.contrib.auth.models import AnonymousUser
from django.test import Client

from audiotrails.common.typedefs import AuthenticatedUser
from audiotrails.users.factories import UserFactory


@pytest.fixture
def user(db) -> AuthenticatedUser:
    return UserFactory()


@pytest.fixture
def anonymous_user() -> AnonymousUser:
    return AnonymousUser


@pytest.fixture
def auth_user(client: Client, user: AuthenticatedUser) -> AuthenticatedUser:
    client.force_login(user)
    return user
