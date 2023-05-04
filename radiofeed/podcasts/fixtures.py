import pytest

from radiofeed.podcasts.factories import (
    create_category,
    create_podcast,
    create_subscription,
)


@pytest.fixture
def podcast(db):
    return create_podcast()


@pytest.fixture
def category(db):
    return create_category()


@pytest.fixture
def subscription(auth_user, podcast):
    return create_subscription(podcast=podcast, subscriber=auth_user)
