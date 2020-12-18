# Django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.http import HttpResponse

# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory
from radiofeed.users.factories import UserFactory


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
def login_user(client):
    password = "t3SzTP4sZ"
    user = UserFactory()
    user.set_password(password)
    user.save()
    client.login(username=user.username, password=password)
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
