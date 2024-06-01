import pytest

from listenwave.episodes.models import Episode
from listenwave.episodes.tests.factories import EpisodeFactory


@pytest.fixture()
def episode() -> Episode:
    return EpisodeFactory()
