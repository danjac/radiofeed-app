import pytest

from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
)


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture
def category() -> Category:
    return CategoryFactory()
