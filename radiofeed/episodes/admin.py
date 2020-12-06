# Django
from django.contrib import admin

# Local
from .models import Episode


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    ordering = ("-pub_date",)
    list_display = ("__str__", "podcast", "pub_date")
    raw_id_fields = ("podcast",)
    search_fields = ("title", "podcast__title")
