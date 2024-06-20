import pytest

from radiofeed.podcasts.models import Category, Podcast, Subscription
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    SubscriptionFactory,
)
from radiofeed.users.models import User


@pytest.fixture()
def podcast() -> Podcast:
    return PodcastFactory()


@pytest.fixture()
def category() -> Category:
    return CategoryFactory()


@pytest.fixture()
def subscription(auth_user: User, podcast: Podcast) -> Subscription:
    return SubscriptionFactory(podcast=podcast, subscriber=auth_user)
