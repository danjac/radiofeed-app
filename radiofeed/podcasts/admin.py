# Django
from django.contrib import admin

# Third Party Libraries
from sorl.thumbnail.admin import AdminImageMixin

# Local
from .models import Category, Podcast


@admin.register(Category)
class CategoryAdmin(AdminImageMixin, admin.ModelAdmin):
    ordering = ("name",)
    list_display = ("name", "parent", "itunes_genre_id")
    search_fields = ("name",)


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub date"
    parameter_name = "pub_date"

    def lookups(self, request, model_admin):
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(pub_date__isnull=False)
        if value == "no":
            return queryset.filter(pub_date__isnull=True)
        return queryset


@admin.register(Podcast)
class PodcastAdmin(AdminImageMixin, admin.ModelAdmin):
    list_filter = (PubDateFilter,)

    ordering = ("-pub_date",)
    list_display = ("__str__", "pub_date")
    search_fields = ("title", "authors")
