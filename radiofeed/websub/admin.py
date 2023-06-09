from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from radiofeed.websub import subscriber
from radiofeed.websub.models import Subscription


class PendingFilter(admin.SimpleListFilter):
    """Filters subscribed."""

    title = "Pending"
    parameter_name = "pending"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Pending"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        return (
            queryset.filter(mode="", num_retries__lt=subscriber.MAX_NUM_RETRIES)
            if self.value() == "yes"
            else queryset
        )


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


class FailedFilter(admin.SimpleListFilter):
    """Filters subscriptions that could not be subscribed."""

    title = "Failed"
    parameter_name = "failed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Failed"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        return (
            queryset.filter(num_retries__gte=subscriber.MAX_NUM_RETRIES)
            if self.value() == "yes"
            else queryset
        )


class SubscribedFilter(admin.SimpleListFilter):
    """Filters subscribed."""

    title = "Subscribed"
    parameter_name = "subscribed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Subscription]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Subscribed"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Subscription]
    ) -> QuerySet[Subscription]:
        """Returns filtered queryset."""

        return (
            queryset.filter(mode=subscriber.SUBSCRIBE)
            if self.value() == "yes"
            else queryset
        )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Django admin for Subscription model."""

    list_filter = (
        SubscribedFilter,
        ConfirmedFilter,
        PingedFilter,
        PendingFilter,
        FailedFilter,
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
