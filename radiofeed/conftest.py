from __future__ import annotations

import pytest

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpResponse
from faker import Faker

from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.podcasts.factories import (
    CategoryFactory,
    PodcastFactory,
    SubscriptionFactory,
)
from radiofeed.users.factories import UserFactory


@pytest.fixture(scope="session")
def faker():
    return Faker()


@pytest.fixture
def locmem_cache(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture(scope="session")
def get_response():
    return lambda req: HttpResponse()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def anonymous_user():
    return AnonymousUser()


@pytest.fixture
def auth_user(client, user):
    client.force_login(user)
    return user


@pytest.fixture
def staff_user(db, client):
    user = UserFactory(is_staff=True)
    client.force_login(user)
    return user


@pytest.fixture
def podcast(db):
    return PodcastFactory()


@pytest.fixture
def episode(db):
    return EpisodeFactory()


@pytest.fixture
def category(db):
    return CategoryFactory()


@pytest.fixture
def subscription(auth_user, podcast):
    return SubscriptionFactory(podcast=podcast, subscriber=auth_user)
