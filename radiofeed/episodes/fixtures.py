import pytest

from radiofeed.episodes.factories import create_episode


@pytest.fixture
def episode(db):
    return create_episode()
