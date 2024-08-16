import pytest

from radiofeed.episodes.models import Episode
from radiofeed.episodes.tests.factories import EpisodeFactory


@pytest.fixture
def episode() -> Episode:
    return EpisodeFactory()
