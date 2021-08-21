from __future__ import annotations

from typing import Iterable

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import pluralize

from jcasts.podcasts import feed_parser, models, scheduler


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ("name",)
    list_display = (
        "name",
        "parent",
    )
    search_fields = ("name",)


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub date"
    parameter_name = "pub_date"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[tuple[str, str]]:
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(pub_date__isnull=False)
        if value == "no":
            return queryset.filter(pub_date__isnull=True)
        return queryset


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[tuple[str, str]]:
        return (("yes", "Promoted"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(promoted=True)
        return queryset


class ActiveFilter(admin.SimpleListFilter):
    title = "Active"
    parameter_name = "active"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[tuple[str, str]]:
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
class PodcastAdmin(admin.ModelAdmin):
    list_filter = (PubDateFilter, ActiveFilter, PromotedFilter)

    list_display = (
        "__str__",
        "source",
        "active",
        "promoted",
        "pub_date",
        "scheduled",
    )

    list_editable = ("promoted",)
    search_fields = ("search_document",)

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "num_episodes",
        "created",
        "updated",
        "parsed",
        "modified",
        "scheduled",
        "pub_date",
        "etag",
        "frequency",
    )

    actions = ["reactivate", "parse_podcast_feeds"]

    @admin.action(description="Re-activate podcasts")
    def reactivate(self, request: HttpRequest, queryset: QuerySet):
        num_updated = queryset.filter(active=False).update(active=True)
        self.message_user(
            request,
            f"{num_updated} podcasts re-activated",
            messages.SUCCESS,
        )

    @admin.action(description="Parse podcast feeds")
    def parse_podcast_feeds(self, request: HttpRequest, queryset: QuerySet):

        for rss in queryset.values_list("rss", flat=True):
            feed_parser.parse_feed.delay(rss, force_update=True)

        self.message_user(
            request,
            f"{queryset.count()} podcast(s) scheduled for update",
            messages.SUCCESS,
        )

    def source(self, obj: models.Podcast) -> str:
        return obj.get_domain()

    def frequency(self, obj: models.Podcast) -> str:
        if (
            freq := scheduler.get_frequency(scheduler.get_recent_pub_dates(obj))
        ) is None:
            return "-"

        if freq.days < 1:
            hours = round(freq.total_seconds() / 3600)
            return f"{hours} hour{pluralize(hours)}"

        return f"{freq.days} day{pluralize(freq.days)}"

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet, search_term: str
    ) -> QuerySet:
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False

    def get_ordering(self, request: HttpRequest) -> Iterable[str]:
        return (
            []
            if request.GET.get("q")
            else [
                "scheduled",
                "-pub_date",
            ]
        )
