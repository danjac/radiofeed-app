from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.db.models import Count, Exists, OuterRef, QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.timesince import timesince, timeuntil

from listenwave.podcasts.models import (
    Category,
    Podcast,
    PodcastQuerySet,
    Recommendation,
    Subscription,
)

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise  # pragma: no cover

    class CategoryWithNumPodcasts(Category):
        """Category with annotated number of podcasts."""

        num_podcasts: int
else:
    StrOrPromise = str
    CategoryWithNumPodcasts = Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for podcast categories."""

    ordering = ("name",)
    list_display = (
        "name",
        "slug",
        "itunes_genre_id",
        "num_podcasts",
    )
    prepopulated_fields: ClassVar = {"slug": ("name",)}
    search_fields = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        """Returns queryset with number of podcasts."""
        return super().get_queryset(request).annotate(num_podcasts=Count("podcasts"))

    def num_podcasts(self, obj: CategoryWithNumPodcasts) -> int:
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

    def queryset(self, request: HttpRequest, queryset: PodcastQuerySet):
        """Returns filtered queryset."""
        match self.value():
            case "yes":
                return queryset.filter(active=True)
            case "no":
                return queryset.filter(active=False)
            case _:
                return queryset


class PodcastTypeFilter(admin.SimpleListFilter):
    """Filters based on parser error."""

    title = "Podcast type"
    parameter_name = "podcast_type"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> list[tuple[str, StrOrPromise]]:
        """Returns lookup values/labels."""
        return Podcast.PodcastType.choices

    def queryset(self, request: HttpRequest, queryset: QuerySet[Podcast]):
        """Returns filtered queryset."""

        match self.value():
            case value if value in Podcast.PodcastType:  # type: ignore[attr-defined]
                return queryset.filter(podcast_type=value)
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
        self, request: HttpRequest, queryset: PodcastQuerySet
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        return queryset.scheduled() if self.value() == "yes" else queryset


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    """Podcast model admin."""

    date_hierarchy = "pub_date"

    list_filter = (
        ActiveFilter,
        PodcastTypeFilter,
        PrivateFilter,
        PromotedFilter,
        ScheduledFilter,
        SubscribedFilter,
    )

    list_display = (
        "__str__",
        "active",
        "pub_date",
        "parsed",
    )

    list_editable = ("active",)

    raw_id_fields = (
        "canonical",
        "recipients",
    )

    readonly_fields = (
        "created",
        "updated",
        "pub_date",
        "num_episodes",
        "parsed",
        "frequency",
        "http_status",
        "next_scheduled_update",
        "modified",
        "etag",
        "content_hash",
    )

    search_fields = ("search",)

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

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: PodcastQuerySet,
        search_term: str,
    ) -> tuple[QuerySet[Podcast], bool]:
        """Search episodes."""
        return (
            (
                queryset.search(search_term).order_by("-rank", "-pub_date"),
                False,
            )
            if search_term
            else super().get_search_results(request, queryset, search_term)
        )

    def get_ordering(self, request: HttpRequest) -> list[str]:
        """Returns default ordering."""
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    """Admin for podcast recommendations."""

    list_display = (
        "podcast",
        "recommended",
        "score",
    )

    readonly_fields = (
        "podcast",
        "recommended",
        "score",
    )
    ordering = ("-score",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Subscription]:
        """Returns queryset with related fields."""
        return super().get_queryset(request).select_related("podcast", "recommended")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for podcast subscriptions."""

    list_display = (
        "podcast",
        "subscriber",
        "created",
    )

    readonly_fields = (
        "podcast",
        "subscriber",
    )

    ordering = ("-created",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Subscription]:
        """Returns queryset with related fields."""
        return super().get_queryset(request).select_related("podcast", "subscriber")
