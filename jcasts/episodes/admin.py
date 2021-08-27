from django.contrib import admin
from django.template.defaultfilters import truncatechars

from jcasts.episodes import models


@admin.register(models.Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("episode_title", "podcast_title", "pub_date")
    list_select_related = ("podcast",)
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)

    def episode_title(self, obj):
        return truncatechars(obj.title, 30)

    episode_title.short_description = "Title"

    def podcast_title(self, obj):
        return truncatechars(obj.podcast.title, 30)

    podcast_title.short_description = "Podcast"

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False

    def get_ordering(self, request):
        return (
            []
            if request.GET.get("q")
            else [
                "-id",
            ]
        )
