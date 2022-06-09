from __future__ import annotations

from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django_object_actions import DjangoObjectActions

from radiofeed.podcasts import models
from radiofeed.podcasts.parsers import feed_parser


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
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:

        match self.value():
            case "yes":
                return queryset.filter(pub_date__isnull=False)
            case "no":
                return queryset.filter(pub_date__isnull=True)
            case "new":
                return queryset.filter(pub_date__isnull=True, parsed__isnull=True)
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


class SubscribedFilter(admin.SimpleListFilter):
    title = "Subscribed"
    parameter_name = "subscribed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (("yes", "Subscribed"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return (
            queryset.annotate(subscribers=Count("subscription")).filter(
                subscribers__gt=0
            )
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

        for podcast_id in queryset.values_list("pk"):
            feed_parser.parse_podcast_feed.delay(podcast_id)

        self.message_user(
            request,
            f"{count} podcast(s) queued for update",
            messages.SUCCESS,
        )

    def parse_podcast_feed(self, request: HttpRequest, obj: models.Podcast) -> None:
        feed_parser.parse_podcast_feed.delay(obj.id)
        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]
