from typing import TypedDict

from allauth.socialaccount.adapter import get_adapter
from django import template
from django.urls import reverse

from listenwave.template import AuthenticatedRequestContext

register = template.Library()


class SettingsItem(TypedDict):
    """A dictionary of settings items."""

    label: str
    icon: str
    url: str


class Settings(TypedDict):
    """A dictionary of settings items."""

    active: SettingsItem
    items: list[SettingsItem]


@register.simple_tag(takes_context=True)
def get_account_settings(context: AuthenticatedRequestContext, active: str) -> Settings:
    """Returns a dictionary of settings items."""

    items = {
        "preferences": SettingsItem(
            label="Preferences",
            icon="adjustments-horizontal",
            url=reverse("users:preferences"),
        ),
        "stats": SettingsItem(
            label="Statistics",
            icon="chart-bar",
            url=reverse("users:stats"),
        ),
        "feeds": SettingsItem(
            label="Import/Export Feeds",
            icon="rss",
            url=reverse("users:import_podcast_feeds"),
        ),
        "email": SettingsItem(
            label="Email Addresses",
            icon="envelope",
            url=reverse("account_email"),
        ),
    }

    if context.request.user.has_usable_password():
        items["password"] = SettingsItem(
            label="Change Password",
            icon="key",
            url=reverse("account_change_password"),
        )
    if get_adapter().list_providers(context.request):
        items["connections"] = SettingsItem(
            label="3rd Party Accounts",
            icon="cloud",
            url=reverse("socialaccount_connections"),
        )

    items["delete_account"] = SettingsItem(
        label="Delete Account",
        icon="trash",
        url=reverse("users:delete_account"),
    )

    return Settings(
        active=items.get(active, items["preferences"]),
        items=list(items.values()),
    )
