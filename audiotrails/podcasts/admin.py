from django.contrib import admin
from django.utils.html import format_html
from sorl.thumbnail.admin import AdminImageMixin

from audiotrails.common.types import admin_action
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


class BlocklistedFilter(admin.SimpleListFilter):
    title = "Blocklist (3+ RSS sync errors)"
    parameter_name = "blocklisted"

    def lookups(self, request, model_admin):
        return (
            ("blocklisted", "Blocklisted"),
            ("allowed", "Allowed"),
            ("danger-zone", "Danger Zone"),
            ("no-errors", "No Errors"),
        )

    def queryset(self, request, queryset):

        if kwargs := {
            "allowed": {"num_retries__lt": 3},
            "blocklisted": {"num_retries__gte": 3},
            "danger-zone": {"num_retries__gt": 0, "num_retries__lt": 3},
            "no-errors": {"num_retries": 0},
        }.get(self.value()):
            queryset = queryset.filter(**kwargs)

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
    list_filter = (PubDateFilter, PromotedFilter, BlocklistedFilter)

    ordering = ("-pub_date",)
    list_display = ("title_with_strikethru", "pub_date", "promoted")
    list_editable = ("promoted",)
    search_fields = ("search_document",)
    raw_id_fields = ("recipients",)

    @admin_action
    def title_with_strikethru(self, obj):
        if obj.num_retries >= 3:
            return format_html(f"<s>{obj.title}</s>")
        return obj.title

    title_with_strikethru.short_description = "Title"

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
