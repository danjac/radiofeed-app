from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from radiofeed.websub import subscriber
from radiofeed.websub.models import Subscription


class ModeFilter(admin.SimpleListFilter):
    """Filters subscriptions based on their mode."""

    title = "Mode"
    parameter_name = "mode"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (
            ("none", "None"),
            ("subscribe", "Subscribe"),
            ("unsubscribe", "Unsubscribe"),
        )

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        match self.value():
            case "subscribe":
                return queryset.filter(mode=subscriber.SUBSCRIBE)
            case "unsubscribe":
                return queryset.filter(mode=subscriber.UNSUBSCRIBE)
            case "none":
                return queryset.filter(mode="")
            case _:
                return queryset


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Django admin for Subscription model."""

    list_filter = (ModeFilter,)

    list_display = (
        "podcast",
        "mode",
    )
    raw_id_fields = ("podcast",)
    readonly_fields = (
        "podcast",
        "hub",
        "topic",
        "mode",
        "secret",
        "expires",
        "num_retries",
    )
