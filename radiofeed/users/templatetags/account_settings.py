import dataclasses

from allauth.socialaccount.adapter import get_adapter
from django import template
from django.http import HttpRequest
from django.template.context import RequestContext
from django.urls import reverse

register = template.Library()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Item:
    """Settings navigation item."""

    name: str
    icon: str
    url: str
    label: str


@register.inclusion_tag("account/_settings.html", takes_context=True)
def settings_dropdown(context: RequestContext, current: str) -> dict:
    """Renders account settings dropdown menu."""

    items = _get_settings_items(context.request)

    try:
        current_item = {item.name: item for item in items}[current]
    except KeyError as exc:
        raise template.TemplateSyntaxError(
            f"{current} is not one of the dropdown items"
        ) from exc

    other_items = [item for item in items if item.name != current]

    return {"current_item": current_item, "items": other_items}


def _get_settings_items(request: HttpRequest) -> list[Item]:
    items = [
        Item(
            name="preferences",
            label="Preferences",
            icon="adjustments-horizontal",
            url=reverse("users:preferences"),
        ),
        Item(
            name="stats",
            label="Statistics",
            icon="chart-bar",
            url=reverse("users:stats"),
        ),
        Item(
            name="feeds",
            label="Import/Export Feeds",
            icon="rss",
            url=reverse("users:import_podcast_feeds"),
        ),
        Item(
            name="email",
            label="Email Addresses",
            icon="envelope",
            url=reverse("account_email"),
        ),
    ]

    if request.user.has_usable_password:
        items = [
            *items,
            Item(
                name="password",
                label="Change Password",
                icon="key",
                url=reverse("account_change_password"),
            ),
        ]

    if get_adapter().list_providers(request):
        items = [
            *items,
            Item(
                name="social_logins",
                label="Social Logins",
                icon="user-group",
                url=reverse("socialaccount_connections"),
            ),
        ]

    return [
        *items,
        Item(
            name="delete_account",
            label="Delete Account",
            icon="trash",
            url=reverse("users:delete_account"),
        ),
    ]
