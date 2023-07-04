import pytest

from radiofeed.podcasts.models import Category, Podcast, Subscription
from radiofeed.podcasts.tests.factories import (
    create_category,
    create_podcast,
    create_subscription,
)
from radiofeed.users.models import User


@pytest.fixture()
def podcast() -> Podcast:
    return create_podcast()


@pytest.fixture()
def category() -> Category:
    return create_category()


@pytest.fixture()
def subscription(auth_user: User, podcast: Podcast) -> Subscription:
    return create_subscription(podcast=podcast, subscriber=auth_user)
