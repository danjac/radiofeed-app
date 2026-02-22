"""E2E tests for HTMX-driven podcast subscription, private feed, and search interactions."""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect


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
def test_add_private_feed(auth_page: Page, live_server):
    """Submitting a valid RSS URL on the add private feed form navigates to private feeds."""
    auth_page.goto(f"{live_server.url}{reverse('podcasts:add_private_feed')}")
    auth_page.get_by_label("RSS Feed URL").fill("https://example.com/private-feed.rss")
    auth_page.get_by_role("button", name="Add Feed").click()
    expect(auth_page).to_have_url(
        f"{live_server.url}{reverse('podcasts:private_feeds')}"
    )


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_remove_private_feed(auth_page: Page, e2e_private_podcast, live_server):
    """Confirming Remove on a private podcast navigates back to the private feeds list."""
    auth_page.goto(f"{live_server.url}{e2e_private_podcast.get_absolute_url()}")
    auth_page.once("dialog", lambda d: d.accept())
    auth_page.get_by_role(
        "button", name="Remove podcast from your Private Feeds"
    ).click()
    expect(auth_page).to_have_url(
        f"{live_server.url}{reverse('podcasts:private_feeds')}"
    )


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_search_form_submit(auth_page: Page, live_server):
    """Typing a query and clicking Search navigates to search results.

    Verifies Alpine x-model binds to the input so the submit button becomes
    enabled, and that the form submits the query as a GET parameter.
    """
    # Start on the results page so the search form is rendered.
    auth_page.goto(
        f"{live_server.url}{reverse('podcasts:search_podcasts')}?search=initial"
    )
    auth_page.get_by_label("Search Ctrl+K").fill("newquery")
    auth_page.get_by_role("button", name="Search", exact=True).click()

    expect(auth_page).to_have_url(re.compile(r"\?search=newquery"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_search_clear_button(auth_page: Page, live_server):
    """Clicking Clear Search empties the input and hides the button.

    The clear button uses x-show="search" and @click sets search='' — pure
    Alpine behaviour with no server round-trip.
    """
    auth_page.goto(
        f"{live_server.url}{reverse('podcasts:search_podcasts')}?search=Test"
    )

    clear_button = auth_page.get_by_label("Clear Search")
    expect(clear_button).to_be_visible()
    clear_button.click()
    expect(clear_button).not_to_be_visible()
