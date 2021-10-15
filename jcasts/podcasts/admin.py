from django.conf import settings
from django.contrib import admin, messages

from jcasts.podcasts import feed_parser, models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ("name",)
    list_display = (
        "name",
        "parent",
    )
    search_fields = ("name",)


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub Date"
    parameter_name = "pub_date"

    def lookups(self, request, model_admin):
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
            ("recent", f"Recent (< {settings.FRESHNESS_THRESHOLD.days} days)"),
            ("stale", f"Stale (> {settings.FRESHNESS_THRESHOLD.days} days)"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.published()
        if value == "no":
            return queryset.unpublished()
        if value == "recent":
            return queryset.recent()
        if value == "stale":
            return queryset.stale()
        return queryset


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(self, request, model_admin):
        return (("yes", "Promoted"),)

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(promoted=True)
        return queryset


class ActiveFilter(admin.SimpleListFilter):
    title = "Active"
    parameter_name = "active"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(active=True)
        if value == "no":
            return queryset.filter(active=False)
        return queryset


@admin.register(models.Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_filter = (
        ActiveFilter,
        PromotedFilter,
        PubDateFilter,
    )

    list_display = (
        "__str__",
        "source",
        "active",
        "promoted",
        "pub_date",
        "parsed",
    )

    list_editable = (
        "active",
        "promoted",
    )
    search_fields = ("title", "rss")

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "parsed",
        "scheduled",
        "modified",
        "pub_date",
        "etag",
        "http_status",
        "exception",
    )

    actions = (
        "parse_podcast_feeds",
        "reactivate_podcast_feeds",
    )

    @admin.action(description="Parse podcast feeds")
    def parse_podcast_feeds(self, request, queryset):

        if queryset.filter(active=False).exists():

            self.message_user(
                request,
                "You cannot parse inactive feeds",
                messages.ERROR,
            )

            return

        num_feeds = queryset.count()

        for podcast in queryset.iterator():
            feed_parser.parse_podcast_feed.delay(podcast.rss)

        self.message_user(
            request,
            f"{num_feeds} podcast(s) scheduled for update",
            messages.SUCCESS,
        )

    def source(self, obj):
        return obj.get_domain()

    def get_ordering(self, request):
        return (
            []
            if request.GET.get("q")
            else [
                "-parsed",
                "-pub_date",
            ]
        )
