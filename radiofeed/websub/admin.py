from __future__ import annotations

from django.contrib import admin

from radiofeed.fast_count import FastCountAdminMixin
from radiofeed.websub.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(FastCountAdminMixin, admin.ModelAdmin):
    """Admin class for Subscription model."""

    list_display = (
        "podcast",
        "expires",
        "requested",
    )
    list_select_related = ("podcast",)

    raw_id_fields = ("podcast",)
