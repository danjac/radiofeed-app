import pytest

from radiofeed.episodes.models import Episode
from radiofeed.episodes.tests.factories import create_episode


@pytest.fixture()
def episode() -> Episode:
    return create_episode()
