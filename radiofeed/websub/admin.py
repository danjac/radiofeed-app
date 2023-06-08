from django.contrib import admin

from radiofeed.websub.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Django admin for Subscription model."""

    list_display = ("podcast", "mode", "requested", "verified")
    raw_id_fields = ("podcast",)
