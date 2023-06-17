import pytest

from radiofeed.episodes.factories import create_episode
from radiofeed.episodes.models import Episode


@pytest.fixture()
def episode() -> Episode:
    return create_episode()
