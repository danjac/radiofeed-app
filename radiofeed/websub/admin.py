from __future__ import annotations

from django.contrib import admin

from radiofeed.websub.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin class for Subscription model."""

    list_display = ("podcast", "mode", "requested", "verified", "expires")
    list_select_related = ("podcast",)
    list_filters = ("mode",)

    raw_id_fields = ("podcast",)
