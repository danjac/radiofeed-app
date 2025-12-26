import pytest

from simplecasts.podcasts.models import Category, Podcast
from simplecasts.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
)


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture
def category() -> Category:
    return CategoryFactory()
