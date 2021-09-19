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


class WebSubFilter(admin.SimpleListFilter):
    title = "WebSub"
    parameter_name = "websub"

    def lookups(self, request, model_admin):
        return (
            ("subscribed", "Subscribed"),
            ("failed", "Failed"),
            ("requested", "Requested"),
            ("pending", "Pending"),
            ("none", "None"),
        )

    def queryset(self, request, queryset):
        return {
            "subscribed": queryset.filter(
                websub_subscribed__isnull=False,
                websub_hub__isnull=False,
            ),
            "failed": queryset.filter(
                websub_hub__isnull=False,
            ).exclude(websub_exception=""),
            "requested": queryset.filter(
                websub_requested__isnull=False,
                websub_hub__isnull=False,
            ),
            "pending": queryset.filter(
                websub_requested__isnull=True,
                websub_subscribed__isnull=True,
                websub_hub__isnull=False,
                websub_exception="",
            ),
            "none": queryset.filter(websub_hub__isnull=True),
        }.setdefault(self.value(), queryset)


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub date"
    parameter_name = "pub_date"

    def lookups(self, request, model_admin):
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(pub_date__isnull=False)
        if value == "no":
            return queryset.filter(pub_date__isnull=True)
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
        WebSubFilter,
    )

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
        "pub_date",
        "scheduled",
        "queued",
        "websub_token",
        "websub_subscribed",
        "websub_requested",
        "etag",
        "http_status",
        "exception",
    )

    actions = ["reactivate", "parse_podcast_feeds"]

    @admin.action(description="Re-activate podcasts")
    def reactivate(self, request, queryset):
        num_updated = queryset.filter(active=False).update(active=True)
        self.message_user(
            request,
            f"{num_updated} podcasts re-activated",
            messages.SUCCESS,
        )

    @admin.action(description="Parse podcast feeds")
    def parse_podcast_feeds(self, request, queryset):

        for rss in queryset.values_list("rss", flat=True):
            feed_parser.parse_feed.delay(rss, force_update=True)

        self.message_user(
            request,
            f"{queryset.count()} podcast(s) scheduled for update",
            messages.SUCCESS,
        )

    def source(self, obj):
        return obj.get_domain()

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False

    def get_ordering(self, request):
        return (
            []
            if request.GET.get("q")
            else [
                "scheduled",
                "-pub_date",
            ]
        )
