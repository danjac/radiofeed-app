from django.contrib import admin

from .models import Episode


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    ordering = ("-id",)
    list_display = ("__str__", "podcast", "pub_date")
    raw_id_fields = ("podcast",)
    search_fields = ("search_document",)
    show_full_result_count = False

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
