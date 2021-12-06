from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from jcasts.websub import models


class StatusFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:

        return (
            ("none", "None"),
            ("pending", "Pending"),
            ("requested", "Requested"),
        ) + tuple(models.Subscription.Status.choices)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if value := self.value():
            if value == "none":
                return queryset.filter(status__isnull=True)
            if value == "pending":
                return queryset.filter(status__isnull=True, requested__isnull=True)
            if value == "requested":
                return queryset.filter(status__isnull=True, requested__isnull=False)
            return queryset.filter(status=value)

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
        "requested",
        "status",
        "status_changed",
        "expires",
        "exception",
    )
