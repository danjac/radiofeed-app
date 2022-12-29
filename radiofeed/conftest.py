from __future__ import annotations

import pytest

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpResponse
from faker import Faker

from radiofeed.episodes.factories import create_episode
from radiofeed.podcasts.factories import (
    create_category,
    create_podcast,
    create_subscription,
)
from radiofeed.users.factories import create_user


@pytest.fixture(scope="session")
def faker():
    faker = Faker()
    yield faker
    faker.unique.clear()


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


@pytest.fixture
def podcast(db):
    return create_podcast()


@pytest.fixture
def episode(db):
    return create_episode()


@pytest.fixture
def category(db):
    return create_category()


@pytest.fixture
def subscription(auth_user, podcast):
    return create_subscription(podcast=podcast, subscriber=auth_user)
