"""Shared fixtures for Playwright e2e tests.

These are available to all app-level test_playwright.py files via
pytest_plugins in the root conftest.py.
"""

from typing import TYPE_CHECKING

import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory
from radiofeed.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.fixture
def e2e_user(transactional_db):
    """Verified user for e2e tests.

    Uses transactional_db so the live server's request thread can see the row.
    Named e2e_user to avoid colliding with the unit-test user fixture.
    """
    user = UserFactory()
    EmailAddress.objects.create(
        user=user,
        email=user.email,
        verified=True,
        primary=True,
    )
    return user


@pytest.fixture
def e2e_podcast(transactional_db):
    """Podcast for e2e tests."""
    return PodcastFactory(title="Test Podcast", description="A test podcast.")


@pytest.fixture
def e2e_episode(transactional_db, e2e_podcast):
    """Episode for e2e tests."""
    return EpisodeFactory(podcast=e2e_podcast, title="Test Episode")


@pytest.fixture
def e2e_subscription(transactional_db, e2e_user, e2e_podcast):
    """Subscription linking e2e_user to e2e_podcast."""
    return SubscriptionFactory(subscriber=e2e_user, podcast=e2e_podcast)


@pytest.fixture
def auth_page(page: Page, e2e_user, live_server) -> Page:
    """Playwright page authenticated as e2e_user."""
    login_url = f"{live_server.url}{reverse('account_login')}"
    page.goto(login_url)
    page.locator('[name="login"]').fill(e2e_user.username)
    page.locator('[name="password"]').fill("testpass")
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url(f"{live_server.url}{reverse('podcasts:subscriptions')}")
    return page
