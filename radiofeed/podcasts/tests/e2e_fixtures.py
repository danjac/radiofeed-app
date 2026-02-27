"""Shared fixtures for Playwright e2e tests.

These are available to all app-level test_playwright.py files via
pytest_plugins in the root conftest.py.
"""

import pytest

from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory


@pytest.fixture
def e2e_podcast(transactional_db):
    """Podcast for e2e tests."""
    return PodcastFactory(title="Test Podcast", description="A test podcast.")


@pytest.fixture
def e2e_subscription(transactional_db, e2e_user, e2e_podcast):
    """Subscription linking e2e_user to e2e_podcast."""
    return SubscriptionFactory(subscriber=e2e_user, podcast=e2e_podcast)


@pytest.fixture
def e2e_private_podcast(transactional_db, e2e_user):
    """Private podcast with e2e_user already subscribed."""
    podcast = PodcastFactory(title="Private Test Podcast", private=True)
    SubscriptionFactory(subscriber=e2e_user, podcast=podcast)
    return podcast
