"""E2E tests for podcast browsing and subscription workflows."""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_subscriptions_page_empty(auth_page: Page, live_server):
    """Subscriptions page for a new user shows an empty-state prompt."""
    auth_page.goto(f"{live_server.url}{reverse('podcasts:subscriptions')}")
    expect(
        auth_page.get_by_text("You're not following any podcasts yet.")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_subscriptions_page_with_podcast(
    auth_page: Page, e2e_subscription, live_server
):
    """Subscriptions page lists podcasts the user has subscribed to."""
    auth_page.goto(f"{live_server.url}{reverse('podcasts:subscriptions')}")
    expect(auth_page.get_by_text(e2e_subscription.podcast.title)).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_discover_page(auth_page: Page, live_server):
    """Discover page is accessible to authenticated users."""
    auth_page.goto(f"{live_server.url}{reverse('podcasts:discover')}")
    expect(auth_page).to_have_title(re.compile("Discover"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_podcast_detail_page(auth_page: Page, e2e_podcast, live_server):
    """Podcast detail page renders the subscribe button for an unsubscribed podcast."""
    auth_page.goto(f"{live_server.url}{e2e_podcast.get_absolute_url()}")
    expect(
        auth_page.get_by_role("button", name="Subscribe to this Podcast")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_subscribe_to_podcast(auth_page: Page, e2e_podcast, live_server):
    """Clicking Subscribe swaps to Unsubscribe via HTMX."""
    auth_page.goto(f"{live_server.url}{e2e_podcast.get_absolute_url()}")
    auth_page.get_by_role("button", name="Subscribe to this Podcast").click()
    expect(
        auth_page.get_by_role("button", name="Unsubscribe from this Podcast")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_unsubscribe_from_podcast(auth_page: Page, e2e_subscription, live_server):
    """Clicking Unsubscribe swaps back to Subscribe via HTMX."""
    auth_page.goto(f"{live_server.url}{e2e_subscription.podcast.get_absolute_url()}")
    auth_page.get_by_role("button", name="Unsubscribe from this Podcast").click()
    expect(
        auth_page.get_by_role("button", name="Subscribe to this Podcast")
    ).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_podcast_episodes_page(auth_page: Page, e2e_episode, live_server):
    """Podcast episodes page lists episodes for the given podcast."""
    auth_page.goto(f"{live_server.url}{e2e_episode.podcast.get_episodes_url()}")
    expect(auth_page.get_by_text(e2e_episode.title)).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_search_podcasts_page(auth_page: Page, e2e_podcast, live_server):
    """Podcast search with a query renders matching results.

    The view redirects to discover when there is no ?search= param.
    """
    url = f"{live_server.url}{reverse('podcasts:search_podcasts')}?search=Test"
    auth_page.goto(url)
    expect(auth_page).to_have_title(re.compile("Search"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_category_list_page(auth_page: Page, live_server):
    """Categories page is accessible to authenticated users."""
    auth_page.goto(f"{live_server.url}{reverse('podcasts:category_list')}")
    expect(auth_page).to_have_title(re.compile("Categories"))
