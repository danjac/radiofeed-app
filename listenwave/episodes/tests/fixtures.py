import pytest

from listenwave.episodes.models import AudioLog, Episode
from listenwave.episodes.tests.factories import AudioLogFactory, EpisodeFactory


@pytest.fixture
def episode() -> Episode:
    return EpisodeFactory()


@pytest.fixture
def audio_log(episode) -> AudioLog:
    return AudioLogFactory(episode=episode)
