from typing import Callable

import pytest

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from faker import Faker

from jcasts.episodes.factories import EpisodeFactory
from jcasts.episodes.models import Episode
from jcasts.podcasts.factories import CategoryFactory, FollowFactory, PodcastFactory
from jcasts.podcasts.models import Category, Follow, Podcast
from jcasts.shared.typedefs import AuthenticatedUser
from jcasts.users.factories import UserFactory


@pytest.fixture
def faker() -> Faker:
    return Faker()


@pytest.fixture
def get_response() -> Callable:
    return lambda req: HttpResponse()


@pytest.fixture
def user(db) -> AuthenticatedUser:
    return UserFactory()


@pytest.fixture
def anonymous_user() -> AnonymousUser:
    return AnonymousUser()


@pytest.fixture
def auth_user(client, user) -> AuthenticatedUser:
    client.force_login(user)
    return user


@pytest.fixture
def podcast(db) -> Podcast:
    return PodcastFactory()


@pytest.fixture
def episode(db) -> Episode:
    return EpisodeFactory()


@pytest.fixture
def category(db) -> Category:
    return CategoryFactory()


@pytest.fixture
def follow(auth_user, podcast) -> Follow:
    return FollowFactory(podcast=podcast, user=auth_user)
