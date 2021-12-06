from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from jcasts.websub import models, subscriber


class StatusFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:

        return (("none", "None"),) + tuple(models.Subscription.Status.choices)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if value := self.value():
            return (
                queryset.filter(status__isnull=True)
                if value == "none"
                else queryset.filter(status=value)
            )

        return queryset


@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_filter = (StatusFilter,)
    list_display = ("podcast", "hub", "status")
    search_fields = ("podcast__title", "topic")

    ordering = ("-created", "-status_changed")

    readonly_fields = (
        "podcast",
        "hub",
        "topic",
        "secret",
        "status",
        "status_changed",
        "expires",
        "exception",
        "response",
    )

    actions = ("resubscribe",)

    def resubscribe(self, request: HttpRequest, queryset: QuerySet) -> None:
        counter: int = 0
        for counter, obj in enumerate(queryset):
            subscriber.subscribe.delay(obj.id)
        self.message_user(
            request,
            f"{counter} subscription(s) resubscribed",
            messages.SUCCESS,
        )
