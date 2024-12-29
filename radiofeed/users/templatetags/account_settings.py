from typing import TypedDict

from allauth.socialaccount.adapter import get_adapter
from django import template
from django.template.context import RequestContext
from django.urls import reverse

register = template.Library()


class Item(TypedDict):
    """Settings navigation item."""

    icon: str
    label: str
    url: str


@register.simple_tag(takes_context=True)
def get_account_settings(context: RequestContext, current: str) -> dict:
    """ "Returns a dictionary of settings items."""
    items = {
        "preferences": Item(
            label="Preferences",
            icon="adjustments-horizontal",
            url=reverse("users:preferences"),
        ),
        "stats": Item(
            label="Statistics",
            icon="chart-bar",
            url=reverse("users:stats"),
        ),
        "feeds": Item(
            label="Import/Export Feeds",
            icon="rss",
            url=reverse("users:import_podcast_feeds"),
        ),
        "email": Item(
            label="Email Addresses",
            icon="envelope",
            url=reverse("account_email"),
        ),
    }

    if context.request.user.has_usable_password:
        items["password"] = Item(
            label="Change Password",
            icon="key",
            url=reverse("account_change_password"),
        )

    if get_adapter().list_providers(context.request):
        items["social_logins"] = Item(
            label="Social Logins",
            icon="user-group",
            url=reverse("socialaccount_connections"),
        )

    items["delete_account"] = Item(
        label="Delete Account",
        icon="trash",
        url=reverse("users:delete_account"),
    )

    current_item = items.pop(current)

    return {
        "items": items.values(),
        "current_item": current_item,
    }
