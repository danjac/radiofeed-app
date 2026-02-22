"""Shared fixtures for Playwright e2e tests.

These are available to all app-level test_playwright.py files via
pytest_plugins in the root conftest.py.
"""

from typing import TYPE_CHECKING

import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from radiofeed.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
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
def e2e_bookmark(transactional_db, e2e_user, e2e_episode):
    """Bookmark linking e2e_user to e2e_episode."""
    return BookmarkFactory(user=e2e_user, episode=e2e_episode)


@pytest.fixture
def e2e_audio_log(transactional_db, e2e_user, e2e_episode):
    """AudioLog linking e2e_user to e2e_episode."""
    return AudioLogFactory(user=e2e_user, episode=e2e_episode)


@pytest.fixture
def e2e_player_audio_log(transactional_db, e2e_user):
    """AudioLog for audio player interaction tests.

    The episode uses a routeable media URL so tests can intercept it with
    page.route() and serve a real WAV file, allowing the <audio> element to
    fire loadedmetadata and enable Alpine's play/pause controls.

    A pre-existing AudioLog means the player renders on page load with
    startPlayer=False, sidestepping Chromium's autoplay policy.
    """
    podcast = PodcastFactory(title="Player Test Podcast")
    episode = EpisodeFactory(
        podcast=podcast,
        title="Player Test Episode",
        media_url="http://audio.test/episode.wav",
        media_type="audio/wav",
    )
    return AudioLogFactory(user=e2e_user, episode=episode)


@pytest.fixture
def e2e_private_podcast(transactional_db, e2e_user):
    """Private podcast with e2e_user already subscribed."""
    podcast = PodcastFactory(title="Private Test Podcast", private=True)
    SubscriptionFactory(subscriber=e2e_user, podcast=podcast)
    return podcast


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
