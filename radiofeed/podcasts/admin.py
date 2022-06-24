import http

from django.contrib import admin, messages
from django.db.models import Count
from django_object_actions import DjangoObjectActions

from radiofeed.podcasts import models
from radiofeed.podcasts.tasks import feed_update


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ("name",)
    list_display = (
        "name",
        "parent",
        "num_podcasts",
    )
    search_fields = ("name",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(num_podcasts=Count("podcast"))

    def num_podcasts(self, obj) -> int:
        return obj.num_podcasts or 0


class ActiveFilter(admin.SimpleListFilter):
    title = "Active"
    parameter_name = "active"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request, queryset):
        match self.value():
            case "yes":
                return queryset.filter(active=True)
            case "no":
                return queryset.filter(active=False)
            case _:
                return queryset


class HttpStatusFilter(admin.SimpleListFilter):
    title = "HTTP Status"
    parameter_name = "http_status"

    def lookups(self, request, model_admin):
        return tuple(
            (status, f"{status} {http.HTTPStatus(status).name}")
            for status in models.Podcast.objects.filter(
                http_status__in=set(status.value for status in http.HTTPStatus)
            )
            .values_list("http_status", flat=True)
            .order_by("http_status")
            .distinct()
        )

    def queryset(self, request, queryset):
        if value := self.value():
            return queryset.filter(http_status=value)
        return queryset


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub Date"
    parameter_name = "pub_date"

    def lookups(self, request, model_admin):
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(self, request, queryset):

        match self.value():
            case "yes":
                return queryset.filter(pub_date__isnull=False)
            case "no":
                return queryset.filter(pub_date__isnull=True)
            case _:
                return queryset


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(self, request, model_admin):
        return (("yes", "Promoted"),)

    def queryset(self, request, queryset):
        return queryset.filter(promoted=True) if self.value() == "yes" else queryset


class SubscribedFilter(admin.SimpleListFilter):
    title = "Subscribed"
    parameter_name = "subscribed"

    def lookups(self, request, model_admin):
        return (("yes", "Subscribed"),)

    def queryset(self, request, queryset):
        return (
            queryset.annotate(subscribers=Count("subscription")).filter(
                subscribers__gt=0
            )
            if self.value() == "yes"
            else queryset
        )


@admin.register(models.Podcast)
class PodcastAdmin(DjangoObjectActions, admin.ModelAdmin):
    date_hierarchy = "pub_date"

    list_filter = (
        ActiveFilter,
        PubDateFilter,
        PromotedFilter,
        SubscribedFilter,
        HttpStatusFilter,
    )

    list_display = (
        "__str__",
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
        "pub_date",
        "modified",
        "etag",
        "http_status",
        "content_hash",
    )

    actions = ("update_podcast_feeds",)

    change_actions = ("update_podcast_feed",)

    def update_podcast_feeds(self, request, queryset):

        count = queryset.count()

        feed_update.map(queryset.values_list("pk", flat=True))

        self.message_user(
            request,
            f"{count} podcast(s) queued for update",
            messages.SUCCESS,
        )

    def update_podcast_feed(self, request, obj):
        feed_update(obj.id)
        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request):
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]
