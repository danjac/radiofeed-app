from __future__ import annotations

from django.contrib import admin

from radiofeed.fast_count import FastCountAdminMixin
from radiofeed.websub.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(FastCountAdminMixin, admin.ModelAdmin):
    """Django admin for Subscription model."""

    search_fields = (
        "hub",
        "topic",
        "podcast__title",
    )

    list_display = (
        "podcast",
        "hub",
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
