"""E2E tests for core site views."""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_index_anonymous(page: Page, live_server):
    """Anonymous users see the landing page with sign-up and log-in links."""
    page.goto(f"{live_server.url}{reverse('index')}")
    expect(page.get_by_role("link", name=re.compile("Sign up to"))).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_index_authenticated(auth_page: Page, live_server):
    """Authenticated users are redirected from the landing page to subscriptions."""
    auth_page.goto(f"{live_server.url}{reverse('index')}")
    expect(auth_page).to_have_url(
        f"{live_server.url}{reverse('podcasts:subscriptions')}"
    )


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_accept_cookies(page: Page, live_server):
    """Clicking 'Accept and close' on the GDPR cookie banner removes it."""
    page.goto(f"{live_server.url}{reverse('index')}")
    banner_button = page.get_by_label("OK, understood")
    expect(banner_button).to_be_visible()
    banner_button.click()
    expect(banner_button).not_to_be_visible()
