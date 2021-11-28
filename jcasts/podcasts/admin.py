from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import timeuntil
from django.utils import timezone
from django_object_actions import DjangoObjectActions

from jcasts.podcasts import feed_parser, models, scheduler


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
            "yes": queryset.active(),
            "no": queryset.inactive(),
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
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return {
            "yes": queryset.published(),
            "no": queryset.unpublished(),
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
            "queued": queryset.queued(),
            "scheduled": queryset.unqueued().scheduled(),
        }.setdefault(value, queryset)


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

    change_actions = (
        "parse_podcast_feed",
        "reschedule_podcast",
    )

    def scheduled(self, obj: models.Podcast):
        if obj.queued:
            return "Queued"

        if (scheduled := obj.get_scheduled()) is None or scheduled < timezone.now():
            return "Pending"

        return timeuntil(scheduled)

    @admin.action(description="Parse podcast feeds")
    def parse_podcast_feeds(self, request: HttpRequest, queryset: QuerySet) -> None:

        self.message_user(
            request,
            f"{feed_parser.parse_podcast_feeds(queryset)} podcast(s) queued for update",
            messages.SUCCESS,
        )

    @admin.action(description="Reactivate podcasts")
    def reactivate_podcasts(self, request: HttpRequest, queryset: QuerySet) -> None:

        inactive = queryset.inactive()

        if num_podcasts := inactive.count():
            inactive.update(active=True, num_failures=0)
            self.message_user(request, f"{num_podcasts} re-activated")
        else:
            self.message_user(request, "No inactive podcasts selected")

    def reschedule_podcast(self, request: HttpRequest, obj: models.Podcast) -> None:
        obj.frequency, obj.frequency_modifier = scheduler.schedule_podcast(obj)
        obj.save(update_fields=["frequency", "frequency_modifier"])
        self.message_user(request, "Podcast rescheduled")

    def parse_podcast_feed(self, request: HttpRequest, obj: models.Podcast) -> None:
        if obj.queued:
            self.message_user(request, "Podcast has already been queued for update")
            return

        if not obj.active:
            self.message_user(request, "Podcast is inactive")
            return

        obj.queued = timezone.now()
        obj.save(update_fields=["queued"])

        feed_parser.parse_podcast_feed.delay(obj.id)
        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request: HttpRequest) -> list[str]:
        return [] if request.GET.get("q") else ["-pub_date"]
