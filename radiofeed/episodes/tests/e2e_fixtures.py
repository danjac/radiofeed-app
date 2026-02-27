"""Shared fixtures for Playwright e2e tests.

These are available to all app-level test_playwright.py files via
pytest_plugins in the root conftest.py.
"""

import pytest

from radiofeed.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.tests.factories import PodcastFactory


@pytest.fixture
def e2e_episode(transactional_db, e2e_podcast):
    """Episode for e2e tests."""
    return EpisodeFactory(podcast=e2e_podcast, title="Test Episode")


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
