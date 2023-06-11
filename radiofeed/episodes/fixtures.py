import pytest

from radiofeed.episodes.factories import create_episode


@pytest.fixture()
def episode():
    return create_episode()
