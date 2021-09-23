from django.contrib import admin, messages

from jcasts.podcasts import feed_parser, models, websub


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
            "subscribed": queryset.websub().filter(
                websub_subscribed__isnull=False,
                websub_exception="",
            ),
            "failed": queryset.websub().filter().exclude(websub_exception=""),
            "requested": queryset.websub().filter(
                websub_requested__isnull=False,
                websub_exception="",
            ),
            "pending": queryset.websub().filter(
                websub_requested__isnull=True,
                websub_subscribed__isnull=True,
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
    )

    list_editable = ("promoted",)
    search_fields = ("search_document",)

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "created",
        "updated",
        "parsed",
        "modified",
        "pub_date",
        "scheduled",
        "queued",
        "websub_token",
        "websub_secret",
        "websub_subscribed",
        "websub_requested",
        "etag",
        "http_status",
        "exception",
    )

    actions = (
        "reactivate",
        "parse_podcast_feeds",
        "reverify_websub_feeds",
    )

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

        for podcast in queryset:
            feed_parser.parse_feed_fast(podcast)

        self.message_user(
            request,
            f"{queryset.count()} podcast(s) scheduled for update",
            messages.SUCCESS,
        )

    @admin.action(description="Reverify websub feeds")
    def reverify_websub_feeds(self, request, queryset):

        for podcast_id in queryset.websub().values_list("pk", flat=True):
            websub.subscribe.delay(podcast_id, reverify=True)

        self.message_user(
            request,
            f"{queryset.count()} websub podcast(s) scheduled for reverification",
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
                "-pub_date",
            ]
        )
