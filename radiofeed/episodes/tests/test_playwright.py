"""E2E tests for HTMX-driven episode interactions."""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_play_episode(auth_page: Page, e2e_episode, live_server):
    """Clicking Play starts the audio player via HTMX."""
    auth_page.goto(f"{live_server.url}{e2e_episode.get_absolute_url()}")
    auth_page.get_by_role("button", name="Open Episode in Player").click()
    expect(auth_page.get_by_role("button", name="Close Player")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_close_player(auth_page: Page, e2e_episode, live_server):
    """Clicking Close Player reverts the button back to Open Episode in Player."""
    auth_page.goto(f"{live_server.url}{e2e_episode.get_absolute_url()}")
    auth_page.get_by_role("button", name="Open Episode in Player").click()
    auth_page.get_by_role("button", name="Close Player").click()
    expect(
        auth_page.get_by_role("button", name="Open Episode in Player")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_remove_audio_log(auth_page: Page, e2e_audio_log, live_server):
    """Confirming Remove on a history entry removes it from the episode page."""
    auth_page.goto(f"{live_server.url}{e2e_audio_log.episode.get_absolute_url()}")
    auth_page.once("dialog", lambda d: d.accept())
    auth_page.locator('button[title="Remove episode from your History"]').click()
    expect(
        auth_page.locator('button[title="Remove episode from your History"]')
    ).not_to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_add_bookmark(auth_page: Page, e2e_episode, live_server):
    """Clicking Bookmark adds the episode and swaps the button label."""
    auth_page.goto(f"{live_server.url}{e2e_episode.get_absolute_url()}")
    auth_page.get_by_role("button", name="Add Episode to your Bookmarks").click()
    expect(
        auth_page.get_by_role("button", name="Remove Episode from your Bookmarks")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_remove_bookmark(auth_page: Page, e2e_bookmark, live_server):
    """Clicking Bookmark on an already-bookmarked episode swaps the button back."""
    auth_page.goto(f"{live_server.url}{e2e_bookmark.episode.get_absolute_url()}")
    auth_page.get_by_role("button", name="Remove Episode from your Bookmarks").click()
    expect(
        auth_page.get_by_role("button", name="Add Episode to your Bookmarks")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_audio_player_play_pause(auth_page: Page, e2e_player_audio_log, live_server):
    """Play/Pause toggle changes the visible control via Alpine x-show.

    A pre-created AudioLog renders the player on page load with startPlayer=False,
    avoiding Chromium's autoplay policy. The episode's media URL is intercepted
    with page.route() to serve a 5-second silent WAV so loadedmetadata fires and
    Alpine's canPlayPause becomes True.
    """
    audio_log = e2e_player_audio_log
    mock_file = (Path(__file__).parent / "mocks" / "episode.wav").read_bytes()
    auth_page.route(
        "http://audio.test/episode.wav",
        lambda route: route.fulfill(
            status=200, content_type="audio/wav", body=mock_file
        ),
    )
    auth_page.goto(f"{live_server.url}{audio_log.episode.get_absolute_url()}")

    # The cookie banner is fixed bottom-0 and would intercept clicks on the
    # audio player (also fixed bottom-0). Dismiss it first.
    cookie_btn = auth_page.get_by_label("OK, understood")
    if cookie_btn.is_visible():
        cookie_btn.click()

    play_btn = auth_page.get_by_role("button", name="Play")
    pause_btn = auth_page.get_by_role("button", name="Pause")

    # Wait for Alpine to initialise and audio metadata to load.
    expect(play_btn).to_be_enabled()

    play_btn.click()
    expect(pause_btn).to_be_visible()

    pause_btn.click()
    expect(play_btn).to_be_visible()
