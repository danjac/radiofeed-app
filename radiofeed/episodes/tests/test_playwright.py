"""E2E tests for episode detail, bookmarks, and history workflows."""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_new_releases_page(auth_page: Page, live_server):
    """New Releases page is accessible to authenticated users."""
    auth_page.goto(f"{live_server.url}{reverse('episodes:index')}")
    expect(auth_page).to_have_title(re.compile("New Releases"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_episode_detail_page(auth_page: Page, e2e_episode, live_server):
    """Episode detail page renders the episode title and Play button."""
    auth_page.goto(f"{live_server.url}{e2e_episode.get_absolute_url()}")
    expect(auth_page.get_by_text(e2e_episode.title)).to_be_visible()
    expect(
        auth_page.get_by_role("button", name="Open Episode in Player")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_play_episode(auth_page: Page, e2e_episode, live_server):
    """Clicking Play starts the audio player via HTMX."""
    auth_page.goto(f"{live_server.url}{e2e_episode.get_absolute_url()}")
    auth_page.get_by_role("button", name="Open Episode in Player").click()
    expect(auth_page.get_by_role("button", name="Close Player")).to_be_visible()


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
def test_bookmarks_page_empty(auth_page: Page, live_server):
    """Bookmarks page shows an empty-state message when no bookmarks exist."""
    auth_page.goto(f"{live_server.url}{reverse('episodes:bookmarks')}")
    expect(
        auth_page.get_by_text("You don't have any Bookmarks at the moment.")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_history_page_empty(auth_page: Page, live_server):
    """History page shows an empty-state message when listening history is empty."""
    auth_page.goto(f"{live_server.url}{reverse('episodes:history')}")
    expect(
        auth_page.get_by_text("Your listening history is empty right now.")
    ).to_be_visible()
