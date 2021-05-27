from django.contrib import admin
from django.db.models import Model
from django.template.defaultfilters import truncatechars

from audiotrails.common.types import admin_action
from audiotrails.episodes.models import Episode


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    ordering = ("-pub_date",)
    list_display = ("episode_title", "podcast_title", "pub_date")
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)

    @admin_action
    def episode_title(self, obj: Model) -> str:
        return truncatechars(obj.title, 30)

    episode_title.short_description = "Title"

    @admin_action
    def podcast_title(self, obj: Model) -> str:
        return truncatechars(obj.title, 30)

    podcast_title.short_description = "Podcast"

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
