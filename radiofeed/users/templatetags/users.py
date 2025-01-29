from allauth.socialaccount.adapter import get_adapter
from django import template
from django.template.context import RequestContext
from django.urls import reverse

from radiofeed.templatetags import DropdownContext

register = template.Library()


@register.simple_tag(takes_context=True)
def get_account_settings(context: RequestContext, selected: str) -> DropdownContext:
    """ "Returns a dictionary of settings items."""
    dropdown = DropdownContext(selected=selected)

    dropdown.add(
        key="preferences",
        label="Preferences",
        icon="adjustments-horizontal",
        url=reverse("users:preferences"),
    )
    dropdown.add(
        key="stats",
        label="Statistics",
        icon="chart-bar",
        url=reverse("users:stats"),
    )
    dropdown.add(
        key="feeds",
        label="Import/Export Feeds",
        icon="rss",
        url=reverse("users:import_podcast_feeds"),
    )
    dropdown.add(
        key="email",
        label="Email Addresses",
        icon="envelope",
        url=reverse("account_email"),
    )
    if context.request.user.has_usable_password:
        dropdown.add(
            key="password",
            label="Change Password",
            icon="key",
            url=reverse("account_change_password"),
        )
    if get_adapter().list_providers(context.request):
        dropdown.add(
            key="social_logins",
            label="Social Logins",
            icon="user-group",
            url=reverse("socialaccount_connections"),
        )

    dropdown.add(
        key="delete_account",
        label="Delete Account",
        icon="trash",
        url=reverse("users:delete_account"),
    )
    return dropdown
