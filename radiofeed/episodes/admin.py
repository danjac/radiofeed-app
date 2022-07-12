from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars

from radiofeed.episodes.models import Episode


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    """Django admin for Episode model."""

    list_display = ("episode_title", "podcast_title", "pub_date")
    list_select_related = ("podcast",)
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)

    def episode_title(self, obj: Episode) -> str:
        """Render truncated episode title."""
        return truncatechars(obj.title, 30)

    episode_title.short_description = "Title"  # type: ignore

    def podcast_title(self, obj: Episode) -> str:
        """Render truncated podcast title."""
        return truncatechars(obj.podcast.title, 30)

    podcast_title.short_description = "Podcast"  # type: ignore

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet, search_term: str
    ) -> QuerySet:
        """Search episodes."""
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False

    def get_ordering(self, request: HttpRequest) -> list[str]:
        """Returns optimized search ordering.

        If unfiltered, just search by id.
        """
        return (
            []
            if request.GET.get("q")
            else [
                "-id",
            ]
        )
