from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import timeuntil
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
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.published()
        if value == "no":
            return queryset.unpublished()
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


class SchedulingFilter(admin.SimpleListFilter):
    title = "Scheduling"
    parameter_name = "scheduling"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        return (
            ("queued", "Queued"),
            ("scheduled", "Scheduled"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        return {
            "queued": queryset.filter(queued__isnull=False),
            "scheduled": queryset.active().scheduled().filter(queued__isnull=True),
        }.setdefault(value, queryset)


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


@admin.register(models.Podcast)
class PodcastAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_filter = (
        FollowedFilter,
        PromotedFilter,
        PubDateFilter,
        SchedulingFilter,
        ResultFilter,
    )

    list_display = (
        "__str__",
        "promoted",
        "pub_date",
    )

    list_editable = ("promoted",)
    search_fields = ("title", "rss")

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "parsed",
        "queued",
        "pub_date",
        "frequency",
        "frequency_modifier",
        "scheduled",
        "last_build_date",
        "modified",
        "etag",
        "http_status",
        "result",
        "exception",
    )

    actions = (
        "parse_podcast_feeds",
        "reactivate_podcasts",
    )

    change_actions = ("parse_podcast_feed",)

    def scheduled(self, obj: models.Podcast):
        if obj.queued:
            return "Queued"

        if (scheduled := obj.get_scheduled()) is None:
            return "Pending"

        return timeuntil(scheduled, depth=1)

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

    def reactivate_podcasts(self, request: HttpRequest, queryset: QuerySet) -> None:

        inactive = queryset.inactive()

        if num_podcasts := inactive.count():
            inactive.update(active=True, num_failures=0)
            self.message_user(request, f"{num_podcasts} re-activated")
        else:
            self.message_user(request, "No inactive podcasts selected")

    reactivate_podcasts.label = "Re-activate podcasts"  # type: ignore
    reactivate_podcasts.description = "Re-activate dead podcasts"  # type: ignore

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return (
            []
            if request.GET.get("q")
            else [
                "parsed",
                "-pub_date",
            ]
        )
