import pytest

from listenwave.podcasts.models import Category, Podcast
from listenwave.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
)


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture
def category() -> Category:
    return CategoryFactory()
