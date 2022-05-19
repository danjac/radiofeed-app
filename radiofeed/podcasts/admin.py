from __future__ import annotations

from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count, F, Q, QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import timeuntil
from django.utils import timezone
from django_object_actions import DjangoObjectActions

from radiofeed.podcasts import models
from radiofeed.podcasts.tasks import parse_podcast_feed


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ("name",)
    list_display = (
        "name",
        "parent",
        "num_podcasts",
    )
    search_fields = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(num_podcasts=Count("podcast"))

    def num_podcasts(self, obj: models.Category) -> int:
        return obj.num_podcasts or 0


class ActiveFilter(admin.SimpleListFilter):
    title = "Active"
    parameter_name = "active"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        match self.value():
            case "yes":
                return queryset.filter(active=True)
            case "no":
                return queryset.filter(active=False)
            case _:
                return queryset


class ResultFilter(admin.SimpleListFilter):
    title = "Result"
    parameter_name = "result"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:

        return (("none", "None"),) + tuple(models.Podcast.Result.choices)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if value := self.value():
            return (
                queryset.filter(result__isnull=True)
                if value == "none"
                else queryset.filter(result=value)
            )

        return queryset


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub Date"
    parameter_name = "pub_date"
    interval = timedelta(days=14)

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
            ("new", "Just added"),
            ("scheduled", "Scheduled"),
            ("frequent", "Frequent (> 14 days)"),
            ("sporadic", "Sporadic (< 14 days)"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        now = timezone.now()
        match self.value():
            case "yes":
                return queryset.filter(pub_date__isnull=False)
            case "no":
                return queryset.filter(pub_date__isnull=True)
            case "new":
                return queryset.filter(pub_date__isnull=True, parsed__isnull=True)
            case "frequent":
                return queryset.filter(
                    pub_date__isnull=False, pub_date__gt=now - self.interval
                )
            case "sporadic":
                return queryset.filter(
                    pub_date__isnull=False, pub_date__lt=now - self.interval
                )
            case _:
                return queryset


class ScheduledFilter(admin.SimpleListFilter):
    title = "Scheduled"
    parameter_name = "scheduled"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Scheduled"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return (
            queryset.filter(
                Q(
                    parsed__isnull=True,
                )
                | Q(parsed__lt=timezone.now() - F("refresh_interval")),
            )
            if self.value() == "yes"
            else queryset
        )


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Promoted"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return queryset.filter(promoted=True) if self.value() == "yes" else queryset


class SubscribedFilter(admin.SimpleListFilter):
    title = "Subscribed"
    parameter_name = "subscribed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Subscribed"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return (
            queryset.with_subscribed().filter(subscribed=True)
            if self.value() == "yes"
            else queryset
        )


@admin.register(models.Podcast)
class PodcastAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_filter = (
        ActiveFilter,
        SubscribedFilter,
        PromotedFilter,
        PubDateFilter,
        ResultFilter,
        ScheduledFilter,
    )

    list_display = (
        "__str__",
        "promoted",
        "parsed",
        "pub_date",
    )

    list_editable = ("promoted",)

    search_fields = ("title", "rss")

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "parsed",
        "refresh_interval",
        "next_scheduled",
        "pub_date",
        "modified",
        "etag",
        "http_status",
        "result",
        "content_hash",
    )

    actions = ("parse_podcast_feeds",)

    change_actions = ("parse_podcast_feed",)

    def parse_podcast_feeds(self, request: HttpRequest, queryset: QuerySet) -> None:

        count = queryset.count()

        for podcast_id in queryset.values_list("pk", flat=True):
            parse_podcast_feed(podcast_id)()

        self.message_user(
            request,
            f"{count} podcast(s) queued for update",
            messages.SUCCESS,
        )

    def parse_podcast_feed(self, request: HttpRequest, obj: models.Podcast) -> None:
        if not obj.active:
            self.message_user(request, "Podcast is inactive")
            return

        parse_podcast_feed(obj.id)()
        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]

    def next_scheduled(self, obj: models.Podcast) -> str:

        if obj.active:
            now = timezone.now()
            scheduled = now if not obj.parsed else obj.parsed + obj.refresh_interval
            return timeuntil(scheduled) if scheduled > now else "Pending"

        return "-"
