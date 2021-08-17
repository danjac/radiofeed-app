from typing import Iterable

from django.contrib import admin
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars

from jcasts.episodes import models
from jcasts.shared.typedefs import admin_action


@admin.register(models.Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("episode_title", "podcast_title", "pub_date")
    list_select_related = ("podcast",)
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)

    @admin_action
    def episode_title(self, obj: models.Episode) -> str:
        return truncatechars(obj.title, 30)

    episode_title.short_description = "Title"

    @admin_action
    def podcast_title(self, obj: models.Episode) -> str:
        return truncatechars(obj.podcast.title, 30)

    podcast_title.short_description = "Podcast"

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False

    def get_ordering(self, request: HttpRequest) -> Iterable[str]:
        return (
            []
            if request.GET.get("q")
            else [
                "-id",
            ]
        )
