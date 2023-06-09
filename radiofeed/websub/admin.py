from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from radiofeed.websub import subscriber
from radiofeed.websub.models import Subscription


class ConfirmedFilter(admin.SimpleListFilter):
    """Filters confirmed."""

    title = "Confirmed"
    parameter_name = "confirmed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Confirmed"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        return (
            queryset.filter(confirmed__isnull=False)
            if self.value() == "yes"
            else queryset
        )


class PingedFilter(admin.SimpleListFilter):
    """Filters pinged."""

    title = "Pinged"
    parameter_name = "pinged"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Pinged"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        return (
            queryset.filter(pinged__isnull=False) if self.value() == "yes" else queryset
        )


class StatusFilter(admin.SimpleListFilter):
    """Filters subscribed."""

    title = "Status"
    parameter_name = "status"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (
            ("subscribed", "Subscribed"),
            ("pending", "Pending"),
            ("failed", "Failed"),
        )

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        match self.value():
            case "subscribed":
                return queryset.filter(mode=subscriber.SUBSCRIBE)
            case "pending":
                return queryset.filter(
                    mode="", num_retries__lt=subscriber.MAX_NUM_RETRIES
                )
            case "failed":
                return queryset.filter(num_retries__gte=subscriber.MAX_NUM_RETRIES)

            case _:
                return queryset


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Django admin for Subscription model."""

    list_filter = (
        StatusFilter,
        ConfirmedFilter,
        PingedFilter,
    )

    list_display = (
        "podcast",
        "hub",
        "mode",
        "confirmed",
        "pinged",
    )
    raw_id_fields = ("podcast",)
    readonly_fields = (
        "podcast",
        "hub",
        "topic",
        "mode",
        "secret",
        "expires",
        "confirmed",
        "pinged",
        "num_retries",
    )
