from __future__ import annotations

from django.conf import settings
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


class WebSubFilter(admin.SimpleListFilter):
    title = "Supports WebSub"
    parameter_name = "websub"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(hub__isnull=False)
        if value == "no":
            return queryset.filter(hub__isnull=True)
        return queryset


class ResultFilter(admin.SimpleListFilter):
    title = "Result"
    parameter_name = "result"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:

        return (("none", "None"),) + tuple(models.Podcast.Result.choices)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()

        if value == "none":
            return queryset.filter(result=None)

        elif value:
            return queryset.filter(result=value)

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
            ("fresh", f"Fresh (< {settings.FRESHNESS_THRESHOLD.days} days)"),
            ("stale", f"Stale (> {settings.FRESHNESS_THRESHOLD.days} days)"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.published()
        if value == "no":
            return queryset.unpublished()
        if value == "fresh":
            return queryset.fresh()
        if value == "stale":
            return queryset.stale()
        return queryset


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Promoted"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(promoted=True)
        return queryset


class QueuedFilter(admin.SimpleListFilter):
    title = "Queued"
    parameter_name = "queued"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Queued"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(queued__isnull=False)
        return queryset


class FollowedFilter(admin.SimpleListFilter):
    title = "Followed"
    parameter_name = "followed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Followed"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        queryset = queryset.with_followed()
        if value == "yes":
            return queryset.filter(followed=True)
        return queryset


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
        value = self.value()
        if value == "yes":
            return queryset.filter(active=True)
        if value == "no":
            return queryset.filter(active=False)
        return queryset


@admin.register(models.Podcast)
class PodcastAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_filter = (
        ActiveFilter,
        FollowedFilter,
        PromotedFilter,
        PubDateFilter,
        QueuedFilter,
        ResultFilter,
        WebSubFilter,
    )

    list_display = (
        "__str__",
        "active",
        "promoted",
        "source",
        "hub",
        "pub_date",
        "scheduled",
    )

    list_editable = (
        "active",
        "promoted",
    )
    search_fields = ("title", "rss")

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "parsed",
        "queued",
        "scheduled",
        "schedule_modifier",
        "last_build_date",
        "modified",
        "pub_date",
        "etag",
        "http_status",
        "result",
        "exception",
        "subscribed",
        "subscribe_status",
        "subscribe_requested",
        "hub_exception",
    )

    actions = (
        "parse_podcast_feeds",
        "reactivate_podcast_feeds",
    )

    change_actions = ("parse_podcast_feed",)

    @admin.action(description="Parse podcast feeds")
    def parse_podcast_feeds(self, request: HttpRequest, queryset: QuerySet) -> None:

        if queryset.filter(active=False).exists():

            self.message_user(
                request,
                "You cannot parse inactive feeds",
                messages.ERROR,
            )

            return

        podcast_ids = list(
            queryset.filter(queued__isnull=True).values_list("pk", flat=True)
        )

        queryset.update(queued=timezone.now())

        for podcast_id in podcast_ids:
            feed_parser.parse_podcast_feed.delay(podcast_id)

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

        obj.queued = timezone.now()

        obj.save(update_fields=["queued", "active"])

        feed_parser.parse_podcast_feed.delay(obj.id)
        self.message_user(request, "Podcast has been queued for update")

    parse_podcast_feed.label = "Parse podcast feed"  # type: ignore
    parse_podcast_feed.description = "Parse podcast feed"  # type: ignore

    def source(self, obj: models.Podcast) -> str:
        return obj.get_domain()

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return (
            []
            if request.GET.get("q")
            else [
                "scheduled",
                "-pub_date",
            ]
        )
