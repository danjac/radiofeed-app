from django.contrib import admin
from sorl.thumbnail.admin import AdminImageMixin

from audiotrails.podcasts.models import Category, Podcast


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
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


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(self, request, model_admin):
        return (("yes", "Promoted"),)

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(promoted=True)
        return queryset


@admin.register(Podcast)
class PodcastAdmin(AdminImageMixin, admin.ModelAdmin):
    list_filter = (PubDateFilter, PromotedFilter)

    ordering = ("-pub_date",)
    list_display = ("title", "pub_date", "promoted")
    list_editable = ("promoted",)
    search_fields = ("search_document",)
    raw_id_fields = ("recipients",)

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
