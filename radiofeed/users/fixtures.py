import pytest
from django.contrib.auth.models import AnonymousUser

from radiofeed.users.factories import create_user


@pytest.fixture
def user(db):
    return create_user()


@pytest.fixture
def anonymous_user():
    return AnonymousUser()


@pytest.fixture
def auth_user(client, user):
    client.force_login(user)
    return user


@pytest.fixture
def staff_user(db, client):
    user = create_user(is_staff=True)
    client.force_login(user)
    return user
