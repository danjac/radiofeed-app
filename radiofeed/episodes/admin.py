from typing import Tuple

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Episode


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    ordering = ("-id",)
    list_display = ("__str__", "podcast", "pub_date")
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet, search_term: str
    ) -> Tuple[QuerySet, bool]:
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
