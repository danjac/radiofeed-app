from django.contrib import admin

from jcasts.websub import models


@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("podcast", "hub", "status")

    ordering = ("-created", "-status_changed")

    readonly_fields = (
        "podcast",
        "hub",
        "topic",
        "callback_url",
        "secret",
        "status",
        "status_changed",
        "expires",
        "exception",
    )
