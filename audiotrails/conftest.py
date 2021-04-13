import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.http import HttpResponse

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.users.factories import UserFactory


@pytest.fixture
def site():
    return Site.objects.get_current()


@pytest.fixture
def get_response():
    return lambda req: HttpResponse()


@pytest.fixture
def user_model():
    return get_user_model()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def anonymous_user():
    return AnonymousUser()


@pytest.fixture
def password():
    return "t3SzTP4sZ"


@pytest.fixture
def login_user(client, user):
    client.force_login(user)
    return user


@pytest.fixture
def login_admin_user(client):
    user = UserFactory(is_staff=True)
    client.force_login(user)
    return user


@pytest.fixture
def category():
    return CategoryFactory()


@pytest.fixture
def podcast():
    return PodcastFactory()


@pytest.fixture
def episode(podcast):
    return EpisodeFactory(podcast=podcast)


@pytest.fixture
def favorite(user, episode):
    return FavoriteFactory(user=user, episode=episode)


@pytest.fixture
def audio_log(user, episode):
    return AudioLogFactory(user=user, episode=episode)


@pytest.fixture
def queue_item(user, episode):
    return QueueItemFactory(user=user, episode=episode)
