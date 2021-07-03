from typing import Type

import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from audiotrails.common.typedefs import AuthenticatedUser
from audiotrails.podcasts.factories import FollowFactory, PodcastFactory
from audiotrails.podcasts.models import Follow, Podcast
from audiotrails.users.factories import UserFactory


@pytest.fixture
def user_model() -> Type[AuthenticatedUser]:
    return get_user_model()


@pytest.fixture
def user(db) -> AuthenticatedUser:
    return UserFactory()


@pytest.fixture
def anonymous_user() -> AnonymousUser:
    return AnonymousUser


@pytest.fixture
def auth_user(client, user) -> AuthenticatedUser:
    client.force_login(user)
    return user


@pytest.fixture
def podcast(db) -> Podcast:
    return PodcastFactory()


@pytest.fixture
def follow(auth_user, podcast) -> Follow:
    return FollowFactory(podcast=podcast, user=auth_user)
