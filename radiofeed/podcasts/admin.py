from __future__ import annotations

import httpx

from django.contrib import admin, messages
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import timeuntil
from django.utils.translation import gettext_lazy as _
from django_object_actions import DjangoObjectActions

from radiofeed.common.fast_count import FastCountAdminMixin
from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.podcasts.models import Category, Podcast


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

    title = _("Active")
    parameter_name = "active"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Podcast]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (
            ("yes", _("Active")),
            ("no", _("Inactive")),
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


class PubDateFilter(admin.SimpleListFilter):
    """Filters podcasts based on last pub date."""

    title = _("Release Date")
    parameter_name = "pub_date"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Podcast]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (
            ("yes", _("With release date")),
            ("no", _("With no release date")),
        )

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        match self.value():
            case "yes":
                return queryset.filter(pub_date__isnull=False)
            case "no":
                return queryset.filter(pub_date__isnull=True)
            case _:
                return queryset


class PromotedFilter(admin.SimpleListFilter):
    """Filters podcasts promoted status."""

    title = _("Promoted")
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Podcast]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", _("Promoted")),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        return queryset.filter(promoted=True) if self.value() == "yes" else queryset


class SubscribedFilter(admin.SimpleListFilter):
    """Filters podcasts based on subscription status."""

    title = "Subscribed"
    parameter_name = "subscribed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Podcast]
    ) -> tuple[tuple[str, str], ...]:
        """Returns lookup values/labels."""
        return (("yes", _("Subscribed")),)

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Podcast]
    ) -> QuerySet[Podcast]:
        """Returns filtered queryset."""
        return (
            queryset.annotate(subscribers=Count("subscriptions")).filter(
                subscribers__gt=0
            )
            if self.value() == "yes"
            else queryset
        )


@admin.register(Podcast)
class PodcastAdmin(DjangoObjectActions, FastCountAdminMixin, admin.ModelAdmin):
    """Podcast model admin."""

    date_hierarchy = "pub_date"

    list_filter = (
        ActiveFilter,
        PubDateFilter,
        PromotedFilter,
        SubscribedFilter,
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
        "frequency",
        "next_scheduled_update",
        "modified",
        "etag",
        "content_hash",
    )

    actions = ("parse_podcast_feeds",)

    change_actions = ("parse_podcast_feed",)

    def parse_podcast_feed(self, request: HttpRequest, obj: Podcast) -> None:
        """Runs feed parser on single podcast."""
        try:
            with httpx.Client(headers={"User-Agent": request.user_agent}) as client:
                feed_parser.parse_feed(obj, client)

        except feed_parser.NotModified:
            self.message_user(
                request, _("Podcast has not been modified"), level=messages.INFO
            )

        except feed_parser.Inaccessible:
            self.message_user(
                request, _("Podcast is no longer accessible"), level=messages.ERROR
            )

        except feed_parser.Duplicate:
            self.message_user(
                request,
                _("Podcast is a duplicate of another podcast"),
                level=messages.ERROR,
            )

        except feed_parser.FeedParserError as e:
            self.message_user(
                request,
                _("Feed parser error: {error}").format(error=str(e)),
                level=messages.ERROR,
            )

        else:
            self.message_user(
                request, _("Podcast has been updated"), level=messages.SUCCESS
            )

    @admin.display(description=_("Estimated Next Update"))
    def next_scheduled_update(self, obj: Podcast):
        """Return estimated next update time."""
        return timeuntil(scheduler.next_scheduled_update(obj))

    def get_ordering(self, request: HttpRequest) -> list[str]:
        """Returns default ordering."""
        return [] if request.GET.get("q") else ["-parsed", "-pub_date"]
