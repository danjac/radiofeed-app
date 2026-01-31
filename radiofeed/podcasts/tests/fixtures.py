from typing import TYPE_CHECKING

import pytest

from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
)

if TYPE_CHECKING:
    from radiofeed.podcasts.models import Category, Podcast


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture
def category() -> Category:
    return CategoryFactory()
