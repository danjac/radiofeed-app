from __future__ import annotations

from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django_object_actions import DjangoObjectActions

from jcasts.podcasts import feed_parser, models


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
        return {
            "yes": queryset.filter(active=True),
            "no": queryset.filter(active=False),
        }.setdefault(self.value(), queryset)


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

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
            ("recent", "Recent (> 14 days)"),
            ("sporadic", "Sporadic (< 14 days)"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        now = timezone.now()
        interval = timedelta(days=14)
        return {
            "yes": queryset.filter(pub_date__isnull=False),
            "no": queryset.filter(pub_date__isnull=True),
            "recent": queryset.filter(
                pub_date__gt=now - interval,
            ),
            "sporadic": queryset.filter(
                pub_date__lt=now - interval,
            ),
        }.setdefault(self.value(), queryset)


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
        return (
            ("yes", "Subscribed"),
            ("no", "Unsubscribed"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if value := self.value():
            queryset = queryset.with_subscribed()

            return {
                "yes": queryset.filter(subscribed=True),
                "no": queryset.filter(subscribed=False),
            }.setdefault(value, queryset)
        return queryset


class FollowedFilter(admin.SimpleListFilter):
    title = "Followed"
    parameter_name = "followed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Followed"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return (
            queryset.with_followed().filter(followed=True)
            if self.value() == "yes"
            else queryset
        )


@admin.register(models.Podcast)
class PodcastAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_filter = (
        ActiveFilter,
        FollowedFilter,
        PromotedFilter,
        PubDateFilter,
        QueuedFilter,
        ResultFilter,
        SubscribedFilter,
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
        "exception",
    )

    actions = ("parse_podcast_feeds",)

    change_actions = ("parse_podcast_feed",)

    def parse_podcast_feeds(self, request: HttpRequest, queryset: QuerySet) -> None:

        podcast_ids = list(
            queryset.filter(queued__isnull=True).values_list("pk", flat=True)
        )
        feed_parser.enqueue_many(podcast_ids, force_update=True)

        self.message_user(
            request,
            f"{len(podcast_ids)} podcast(s) queued for update",
            messages.SUCCESS,
        )

    def parse_podcast_feed(self, request: HttpRequest, obj: models.Podcast) -> None:
        if obj.queued:
            self.message_user(request, "Podcast has already been queued for update")
            return

        if not obj.active:
            self.message_user(request, "Podcast is inactive")
            return

        feed_parser.enqueue(obj.id, force_update=True)

        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]
