import pytest
from django.test import Client

from simplecasts.episodes.middleware import PlayerDetails
from simplecasts.episodes.models import AudioLog, Episode
from simplecasts.episodes.tests.factories import AudioLogFactory, EpisodeFactory
from simplecasts.users.models import User


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
