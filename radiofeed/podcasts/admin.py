from django.contrib import admin
from django.db.models import Count, Exists, OuterRef, QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.timesince import timesince, timeuntil

from radiofeed.fast_count import FastCountAdminMixin
from radiofeed.podcasts.models import Category, Podcast, Subscription


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for podcast categories."""

    ordering = ("name",)
    list_display = (
        "name",
        "parent",
        "num_podcasts",
    )
    search_fields = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        """Returns queryset with number of podcasts."""
        return super().get_queryset(request).annotate(num_podcasts=Count("podcasts"))

    def num_podcasts(self, obj: Category) -> int:
        """Returns number of podcasts in this category."""
        return obj.num_podcasts or 0


class ActiveFilter(admin.SimpleListFilter):
    """Filters active/inactive podcasts."""

    title = "Active"
    parameter_name = "active"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Podcast]):
        """Returns filtered queryset."""
        match self.value():
            case "yes":
                return queryset.filter(active=True)
            case "no":
                return queryset.filter(active=False)
            case _:
                return queryset


class ParserErrorFilter(admin.SimpleListFilter):
    """Filters based on parser error."""

    title = "Parser Error"
    parameter_name = "parser_error"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> list[tuple[str, str]]:
        """Returns lookup values/labels."""
        return Podcast.ParserError.choices

    def queryset(self, request: HttpRequest, queryset: QuerySet[Podcast]):
        """Returns filtered queryset."""

        match self.value():
            case value if value in Podcast.ParserError:  # type: ignore[attr-defined]
                return queryset.filter(parser_error=value)
            case _:
                return queryset


class PubDateFilter(admin.SimpleListFilter):
    """Filters podcasts based on last pub date."""

    title = "Pub Date"
    parameter_name = "pub_date"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        match self.value():
            case "yes":
                return queryset.published()
            case "no":
                return queryset.published(published=False)
            case _:
                return queryset


class PromotedFilter(admin.SimpleListFilter):
    """Filters podcasts promoted status."""

    title = "Promoted"
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Promoted"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        return queryset.filter(promoted=True) if self.value() == "yes" else queryset


class PrivateFilter(admin.SimpleListFilter):
    """Filters podcasts private status."""

    title = "Private"
    parameter_name = "private"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Private"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        return queryset.filter(private=True) if self.value() == "yes" else queryset


class SubscribedFilter(admin.SimpleListFilter):
    """Filters podcasts based on subscription status."""

    title = "Subscribers"
    parameter_name = "subscribed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Subscribed"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""

        if self.value() == "yes":
            return queryset.alias(
                has_subscribers=Exists(
                    Subscription.objects.filter(podcast=OuterRef("pk"))
                )
            ).filter(has_subscribers=True)

        return queryset


class ScheduledFilter(admin.SimpleListFilter):
    """Filters podcasts scheduled for update."""

    title = "Scheduled"
    parameter_name = "scheduled"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", "Scheduled"),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        return queryset.scheduled() if self.value() == "yes" else queryset


@admin.register(Podcast)
class PodcastAdmin(FastCountAdminMixin, admin.ModelAdmin):
    """Podcast model admin."""

    date_hierarchy = "pub_date"

    list_filter = (
        ActiveFilter,
        PubDateFilter,
        SubscribedFilter,
        PromotedFilter,
        PrivateFilter,
        ScheduledFilter,
        ParserErrorFilter,
    )

    list_display = (
        "__str__",
        "active",
        "promoted",
        "pub_date",
        "parsed",
    )

    search_fields = ("title", "rss")

    raw_id_fields = ("recipients",)

    readonly_fields = (
        "pub_date",
        "parsed",
        "parser_error",
        "frequency",
        "next_scheduled_update",
        "modified",
        "etag",
        "content_hash",
    )

    actions = ("make_promoted",)

    @admin.display(description="Estimated Next Update")
    def next_scheduled_update(self, obj: Podcast) -> str:
        """Return estimated next update time."""
        if obj.active:
            scheduled = obj.get_next_scheduled_update()
            return (
                f"{timesince(scheduled)} ago"
                if scheduled < timezone.now()
                else timeuntil(scheduled)
            )
        return "-"

    def get_ordering(self, request: HttpRequest) -> list[str]:
        """Returns default ordering."""
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]

    @admin.action(description="Promote podcasts")
    def make_promoted(self, request: HttpRequest, queryset: QuerySet[Podcast]) -> None:
        """Promotes podcasts."""
        queryset.update(promoted=True)
