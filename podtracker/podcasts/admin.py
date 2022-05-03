from __future__ import annotations

from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django_object_actions import DjangoObjectActions

from podtracker.podcasts import models
from podtracker.podcasts.tasks import parse_podcast_feed


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ("name",)
    list_display = (
        "name",
        "parent",
    )
    search_fields = ("name",)


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
            ("recent", "Recent (> 14 days)"),
            ("sporadic", "Sporadic (< 14 days)"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        now = timezone.now()
        match self.value():
            case "yes":
                return queryset.published()
            case "no":
                return queryset.unpublished()
            case "new":
                return queryset.unpublished().filter(parsed__isnull=True)
            case "recent":
                return queryset.published().filter(pub_date__gt=now - self.interval)
            case "sporadic":
                return queryset.published().filter(pub_date__lt=now - self.interval)
            case _:
                return queryset


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Promoted"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return queryset.filter(promoted=True) if self.value() == "yes" else queryset


class QueuedFilter(admin.SimpleListFilter):
    title = "Queued"
    parameter_name = "queued"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Queued"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return (
            queryset.filter(queued__isnull=False) if self.value() == "yes" else queryset
        )


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
        QueuedFilter,
        ResultFilter,
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
        "queued",
        "pub_date",
        "modified",
        "etag",
        "http_status",
        "result",
        "content_hash",
    )

    actions = (
        "dequeue",
        "parse_podcast_feeds",
    )

    change_actions = ("parse_podcast_feed",)

    def dequeue(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.filter(queued__isnull=False).update(queued=None)
        self.message_user(request, "Podcasts removed from queue", messages.SUCCESS)

    dequeue.short_description = "Remove podcasts from queue"  # type: ignore

    def parse_podcast_feeds(self, request: HttpRequest, queryset: QuerySet) -> None:

        count = queryset.count()
        now = timezone.now()

        print("updating queued...")
        queryset.update(updated=now, queued=now)

        for podcast_id in queryset.values_list("pk", flat=True):
            print("podcast_id", podcast_id)
            parse_podcast_feed(podcast_id)()

        self.message_user(
            request,
            f"{count} podcast(s) queued for update",
            messages.SUCCESS,
        )

    def parse_podcast_feed(self, request: HttpRequest, obj: models.Podcast) -> None:
        if obj.queued:
            self.message_user(request, "Podcast has already been queued for update")
            return

        if not obj.active:
            self.message_user(request, "Podcast is inactive")
            return

        obj.queued = obj.updated = timezone.now()
        obj.save()

        parse_podcast_feed(obj.id)()
        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]
