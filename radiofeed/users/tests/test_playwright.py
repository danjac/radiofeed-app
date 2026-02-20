"""E2E tests for user account workflows."""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_login_valid_credentials(page: Page, e2e_user, live_server):
    login_url = f"{live_server.url}{reverse('account_login')}"
    page.goto(login_url)
    page.locator('[name="login"]').fill(e2e_user.username)
    page.locator('[name="password"]').fill("testpass")
    page.get_by_role("button", name="Sign In").click()
    subscriptions_url = f"{live_server.url}{reverse('podcasts:subscriptions')}"
    page.wait_for_url(subscriptions_url)
    expect(page).to_have_url(subscriptions_url)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_login_invalid_credentials(page: Page, e2e_user, live_server):
    login_url = f"{live_server.url}{reverse('account_login')}"
    page.goto(login_url)
    page.locator('[name="login"]').fill(e2e_user.username)
    page.locator('[name="password"]').fill("wrongpassword")
    page.get_by_role("button", name="Sign In").click()
    # Allauth adds a non-field error (not a per-field error) on bad credentials,
    # so we verify the user stays on the login page with the form still present.
    expect(page).to_have_url(login_url)
    expect(page.get_by_role("button", name="Sign In")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_unauthenticated_redirect_to_login(page: Page, live_server):
    """Protected pages redirect unauthenticated visitors to the login page."""
    page.goto(f"{live_server.url}{reverse('podcasts:subscriptions')}")
    expect(page).to_have_url(re.compile(r"/account/login/"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_logout(auth_page: Page, live_server):
    auth_page.locator("#user-dropdown-btn").click()
    auth_page.get_by_role("button", name="Logout").click()
    # After logout allauth redirects to the home page; the login link appears.
    expect(auth_page.get_by_role("link", name="log in")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_preferences_page(auth_page: Page, live_server):
    """User preferences page renders the settings form."""
    auth_page.goto(f"{live_server.url}{reverse('users:preferences')}")
    expect(auth_page).to_have_title(re.compile("Preferences"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_stats_page(auth_page: Page, live_server):
    """User statistics page is accessible."""
    auth_page.goto(f"{live_server.url}{reverse('users:stats')}")
    expect(auth_page).to_have_title(re.compile("Statistics"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_import_feeds_page(auth_page: Page, live_server):
    """OPML import/export page is accessible."""
    auth_page.goto(f"{live_server.url}{reverse('users:import_podcast_feeds')}")
    expect(auth_page).to_have_title(re.compile("Import/Export Feeds"))


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_delete_account_page(auth_page: Page, live_server):
    """Delete account page renders a confirmation form."""
    auth_page.goto(f"{live_server.url}{reverse('users:delete_account')}")
    expect(auth_page).to_have_title(re.compile("Delete Account"))
