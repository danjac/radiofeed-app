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

    icon: str
    url: str
    label: str


@register.inclusion_tag("account/settings_base#dropdown.html", takes_context=True)
def settings_dropdown(context: RequestContext, current: str) -> dict:
    """Renders account settings dropdown menu."""
    items = _get_settings_items(context.request)

    try:
        current_item = items.pop(current)
    except KeyError as exc:
        raise template.TemplateSyntaxError(
            f"{current} is not one of the dropdown items"
        ) from exc

    return {"current_item": current_item, "items": items.values()}


def _get_settings_items(request: HttpRequest) -> dict[str, Item]:
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

    if request.user.has_usable_password:
        items["password"] = Item(
            label="Change Password",
            icon="key",
            url=reverse("account_change_password"),
        )

    if get_adapter().list_providers(request):
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

    return items
