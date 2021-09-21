import pytest

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpResponse
from faker import Faker

from jcasts.episodes.factories import AudioLogFactory, EpisodeFactory
from jcasts.podcasts.factories import CategoryFactory, FollowFactory, PodcastFactory
from jcasts.users.factories import UserFactory


@pytest.fixture
def faker():
    return Faker()


@pytest.fixture
def locmem_cache(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture
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
def podcast(db):
    return PodcastFactory()


@pytest.fixture
def episode(db):
    return EpisodeFactory()


@pytest.fixture
def category(db):
    return CategoryFactory()


@pytest.fixture
def follow(auth_user, podcast):
    return FollowFactory(podcast=podcast, user=auth_user)


@pytest.fixture
def player_audio_log(auth_user, episode):
    return AudioLogFactory(
        user=auth_user,
        episode=episode,
        is_playing=True,
        current_time=500,
    )
