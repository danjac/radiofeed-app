from django.contrib import admin
from django.db import connections
from django.template.defaultfilters import truncatechars

from .models import Episode


class CountProxy:
    # https://stackoverflow.com/questions/41467751/how-to-override-queryset-count-method-in-djangos-admin-list

    def __init__(self, query):
        self.query = query
        self.db = self.query.db

    def __call__(self):
        query = self.query._query
        if not (query.group_by or query.where or query.distinct):
            cursor = connections[self.db].cursor()
            cursor.execute(
                "SELECT reltuples FROM pg_class WHERE relname = %s",
                [self.query.model._meta.db_table],
            )
            n = int(cursor.fetchone()[0])
            if n >= 1000:
                return n  # exact count for small tables
            else:
                return self.query.get_count(using=self.db)
        else:
            return self.query.get_count(using=self.db)


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    ordering = ("-pub_date",)
    list_display = ("episode_title", "podcast_title", "pub_date")
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)
    show_full_result_count = False

    def episode_title(self, obj):
        return truncatechars(obj.title, 30)

    episode_title.short_description = "Title"

    def podcast_title(self, obj):
        return truncatechars(obj.title, 30)

    podcast_title.short_description = "Podcast"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs.count = CountProxy(qs)
        return qs

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
