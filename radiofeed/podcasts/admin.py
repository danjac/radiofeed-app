import http

from django.contrib import admin, messages
from django.db.models import Count
from django_object_actions import DjangoObjectActions

from radiofeed.feedparser.tasks import parse_feed
from radiofeed.podcasts import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for podcast categories."""

    ordering = ("name",)
    list_display = (
        "name",
        "parent",
        "num_podcasts",
    )
    search_fields = ("name",)

    def get_queryset(self, request):
        """Returns queryset with number of podcasts.

        Args:
            request (HttpRequest)

        Returns:
            QuerySet: annotated queryset with `num_podcasts`
        """
        return super().get_queryset(request).annotate(num_podcasts=Count("podcast"))

    def num_podcasts(self, obj):
        """Returns number of podcasts in this category.

        Args:
            obj (Podcast)

        Returns:
            int
        """
        return obj.num_podcasts or 0


class ActiveFilter(admin.SimpleListFilter):
    """Filters active/inactive podcasts."""

    title = "Active"
    parameter_name = "active"

    def lookups(self, request, model_admin):
        """Returns lookup values/labels.

        Args:
            request (HttpRequest)
            model_admin (ModelAdmin)

        Returns:
            tuple[tuple[str, str]]
        """
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request, queryset):
        """Returns filtered queryset.

        Args:
            request (HttpRequest)
            queryset (QuerySet)

        Returns:
            QuerySet
        """
        match self.value():
            case "yes":
                return queryset.filter(active=True)
            case "no":
                return queryset.filter(active=False)
            case _:
                return queryset


class ParseResultFilter(admin.SimpleListFilter):
    """Filters podcasts based on last feed parser result."""

    title = "Parse Result"
    parameter_name = "parse_result"

    def lookups(self, request, model_admin):
        """Returns lookup values/labels.

        Args:
            request (HttpRequest)
            model_admin (ModelAdmin)

        Returns:
            tuple[tuple[str, str]]
        """
        return (("none", "None"),) + tuple(models.Podcast.ParseResult.choices)

    def queryset(self, request, queryset):
        """Returns filtered queryset.

        Args:
            request (HttpRequest)
            queryset (QuerySet)

        Returns:
            QuerySet
        """
        match value := self.value():
            case "none":
                return queryset.filter(parse_result=None)
            case value if value in models.Podcast.ParseResult:
                return queryset.filter(parse_result=value)
            case _:
                return queryset


class HttpStatusFilter(admin.SimpleListFilter):
    """Filters podcasts based on last feed parser HTTP status."""

    title = "HTTP Status"
    parameter_name = "http_status"

    def lookups(self, request, model_admin):
        """Returns lookup values/labels.

        Args:
            request (HttpRequest)
            model_admin (ModelAdmin)

        Returns:
            tuple[tuple[str, str]]
        """
        return tuple(
            (status, f"{status} {http.HTTPStatus(status).name}")
            for status in models.Podcast.objects.filter(
                http_status__in={status.value for status in http.HTTPStatus}
            )
            .values_list("http_status", flat=True)
            .order_by("http_status")
            .distinct()
        )

    def queryset(self, request, queryset):
        """Returns filtered queryset.

        Args:
            request (HttpRequest)
            queryset (QuerySet)

        Returns:
            QuerySet
        """
        if value := self.value():
            return queryset.filter(http_status=value)
        return queryset


class PubDateFilter(admin.SimpleListFilter):
    """Filters podcasts based on last pub date."""

    title = "Pub Date"
    parameter_name = "pub_date"

    def lookups(self, request, model_admin):
        """Returns lookup values/labels.

        Args:
            request (HttpRequest)
            model_admin (ModelAdmin)

        Returns:
            tuple[tuple[str, str]]
        """
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(self, request, queryset):
        """Returns filtered queryset.

        Args:
            request (HttpRequest)
            queryset (QuerySet)

        Returns:
            QuerySet
        """
        match self.value():
            case "yes":
                return queryset.filter(pub_date__isnull=False)
            case "no":
                return queryset.filter(pub_date__isnull=True)
            case _:
                return queryset


class PromotedFilter(admin.SimpleListFilter):
    """Filters podcasts promoted status."""

    title = "Promoted"
    parameter_name = "promoted"

    def lookups(self, request, model_admin):
        """Returns lookup values/labels.

        Args:
            request (HttpRequest)
            model_admin (ModelAdmin)

        Returns:
            tuple[tuple[str, str]]
        """
        return (("yes", "Promoted"),)

    def queryset(self, request, queryset):
        """Returns filtered queryset.

        Args:
            request (HttpRequest)
            queryset (QuerySet)

        Returns:
            QuerySet
        """
        return queryset.filter(promoted=True) if self.value() == "yes" else queryset


class SubscribedFilter(admin.SimpleListFilter):
    """Filters podcasts based on subscription status."""

    title = "Subscribed"
    parameter_name = "subscribed"

    def lookups(self, request, model_admin):
        """Returns lookup values/labels.

        Args:
            request (HttpRequest)
            model_admin (ModelAdmin)

        Returns:
            tuple[tuple[str, str]]
        """
        return (("yes", "Subscribed"),)

    def queryset(self, request, queryset):
        """Returns filtered queryset.

        Args:
            request (HttpRequest)
            queryset (QuerySet)

        Returns:
            QuerySet
        """
        return (
            queryset.annotate(subscribers=Count("subscription")).filter(
                subscribers__gt=0
            )
            if self.value() == "yes"
            else queryset
        )


@admin.register(models.Podcast)
class PodcastAdmin(DjangoObjectActions, admin.ModelAdmin):
    """Podcast model admin."""

    date_hierarchy = "pub_date"

    list_filter = (
        ActiveFilter,
        PubDateFilter,
        PromotedFilter,
        SubscribedFilter,
        ParseResultFilter,
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
        "parse_result",
        "content_hash",
    )

    actions = ("parse_podcast_feeds",)

    change_actions = ("parse_podcast_feed",)

    def parse_podcast_feeds(self, request, queryset):
        """Runs feed parser on all podcasts in selection.

        Args:
            request (HttpRequest): request
            queryset (QuerySet): podcast queryset
        """
        count = queryset.count()

        parse_feed.map(queryset.values_list("pk", flat=True))

        self.message_user(
            request,
            f"{count} podcast(s) queued for update",
            messages.SUCCESS,
        )

    def parse_podcast_feed(self, request, obj):
        """Runs feed parser on single podcast.

        Args:
            request (HttpRequest): request
            obj (Podcast): Podcast instance
        """
        parse_feed(obj.id)
        self.message_user(request, "Podcast has been queued for update")

    def get_ordering(self, request):
        """Returns default ordering.

        Args:
            request (HttpRequest)

        Returns:
            list[str]
        """
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]
