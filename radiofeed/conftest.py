from typing import Type

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.http import HttpResponse
from django.test import Client

from radiofeed.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from radiofeed.episodes.models import AudioLog, Episode, Favorite, QueueItem
from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.users.factories import UserFactory


@pytest.fixture
def site() -> Site:
    return Site.objects.get_current()


@pytest.fixture
def get_response() -> HttpResponse:
    return lambda req: HttpResponse()


@pytest.fixture
def user_model() -> Type[settings.AUTH_USER_MODEL]:
    return get_user_model()


@pytest.fixture
def user() -> settings.AUTH_USER_MODEL:
    return UserFactory()


@pytest.fixture
def anonymous_user() -> AnonymousUser:
    return AnonymousUser()


@pytest.fixture
def password() -> str:
    return "t3SzTP4sZ"


@pytest.fixture
def login_user(client: Client, password: str) -> settings.AUTH_USER_MODEL:
    return _make_login_user(client, password)


@pytest.fixture
def login_admin_user(client: Client, password: str) -> settings.AUTH_USER_MODEL:
    return _make_login_user(client, password, is_staff=True)


@pytest.fixture
def category() -> Category:
    return CategoryFactory()


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture
def episode(podcast: Podcast) -> Episode:
    return EpisodeFactory(podcast=podcast)


@pytest.fixture
def favorite(user: settings.AUTH_USER_MODEL, episode: Episode) -> Favorite:
    return FavoriteFactory(user=user, episode=episode)


@pytest.fixture
def audio_log(user: settings.AUTH_USER_MODEL, episode: Episode) -> AudioLog:
    return AudioLogFactory(user=user, episode=episode)


@pytest.fixture
def queue_item(user: settings.AUTH_USER_MODEL, episode: Episode) -> QueueItem:
    return QueueItemFactory(user=user, episode=episode)


def _make_login_user(
    client: Client, password: str, **defaults
) -> settings.AUTH_USER_MODEL:
    user = UserFactory(**defaults)
    user.set_password(password)
    user.save()
    client.login(username=user.username, password=password)
    return user
