from typing import Iterable, Tuple

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from sorl.thumbnail.admin import AdminImageMixin

from .models import Category, Podcast


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ("name",)
    list_display = ("name", "parent", "itunes_genre_id")
    search_fields = ("name",)


class PubDateFilter(admin.SimpleListFilter):
    title = "Pub date"
    parameter_name = "pub_date"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[Tuple[str, str]]:
        return (
            ("yes", "With pub date"),
            ("no", "With no pub date"),
        )

    def queryset(self, request: HttpRequest, queryset) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(pub_date__isnull=False)
        if value == "no":
            return queryset.filter(pub_date__isnull=True)
        return queryset


class SyncErrorFilter(admin.SimpleListFilter):
    title = "Blocklist (3+ sync errors)"
    parameter_name = "blocklisted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[Tuple[str, str]]:
        return (
            ("yes", "Blocklisted"),
            ("no", "Allowed"),
        )

    def queryset(self, request: HttpRequest, queryset) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(num_retries__gte=3)
        if value == "no":
            return queryset.filter(num_retries=0)
        return queryset


class PromotedFilter(admin.SimpleListFilter):
    title = "Promoted"
    parameter_name = "promoted"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[Tuple[str, str]]:
        return (("yes", "Promoted"),)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == "yes":
            return queryset.filter(promoted=True)
        return queryset


@admin.register(Podcast)
class PodcastAdmin(AdminImageMixin, admin.ModelAdmin):
    list_filter = (PubDateFilter, PromotedFilter, SyncErrorFilter)

    ordering = ("-pub_date",)
    list_display = ("title_with_strikethru", "pub_date", "promoted")
    list_editable = ("promoted",)
    search_fields = ("search_document",)
    raw_id_fields = ("recipients",)

    def title_with_strikethru(self, obj: Podcast) -> str:
        if obj.num_retries >= 3:
            return mark_safe(f"<s>{obj.title}</s>")
        return obj.title

    title_with_strikethru.short_description = "Title"  # type: ignore

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet, search_term: str
    ) -> Tuple[QuerySet, bool]:
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        return queryset.search(search_term).order_by("-rank", "-pub_date"), False
