from collections.abc import Callable, Generator

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.signals import user_logged_in
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.test import Client

from simplecasts.middleware import PlayerDetails
from simplecasts.models import AudioLog, Category, Episode, Podcast, User
from simplecasts.tests.factories import (
    AudioLogFactory,
    CategoryFactory,
    EpisodeFactory,
    PodcastFactory,
    UserFactory,
)


@pytest.fixture
def site():
    return Site.objects.get_current()


@pytest.fixture(autouse=True)
def _settings_overrides(settings) -> None:
    """Default settings for all tests."""
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }
    settings.ALLOWED_HOSTS = ["example.com", "testserver", "localhost"]
    settings.LOGGING = None
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def _locmem_cache(settings) -> Generator:
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture(scope="session", autouse=True)
def _disable_update_last_login() -> None:
    """
    Disable the update_last_login signal receiver to reduce login overhead.

    See: https://adamj.eu/tech/2024/09/18/django-test-speed-last-login/
    """
    user_logged_in.disconnect(dispatch_uid="update_last_login")


@pytest.fixture(scope="session")
def get_response() -> Callable[[HttpRequest], HttpResponse]:
    return lambda req: HttpResponse()


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture
def category() -> Category:
    return CategoryFactory()


@pytest.fixture
def user() -> User:
    return UserFactory()


@pytest.fixture
def anonymous_user() -> AnonymousUser:
    return AnonymousUser()


@pytest.fixture
def auth_user(client: Client, user: User) -> User:
    client.force_login(user)
    return user


@pytest.fixture
def staff_user(client: Client) -> User:
    user = UserFactory(is_staff=True)
    client.force_login(user)
    return user


@pytest.fixture
def episode() -> Episode:
    return EpisodeFactory()


@pytest.fixture
def audio_log(episode: Episode) -> AudioLog:
    return AudioLogFactory(episode=episode)


@pytest.fixture
def player_episode(auth_user: User, client: Client, episode: Episode) -> Episode:
    """Fixture that creates an AudioLog for the given user and episode"""
    AudioLogFactory(user=auth_user, episode=episode)

    session = client.session
    session[PlayerDetails.session_id] = episode.pk
    session.save()

    return episode
