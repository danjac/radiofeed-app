from __future__ import annotations

from django.http import HttpRequest

from radiofeed.db.fast_count import FastCounter, FastCountPaginator
from radiofeed.types import T_ModelAdmin


class FastCountAdminMixin(T_ModelAdmin):
    """Implements fast count. Use with queryset implementing FastCounter."""

    paginator = FastCountPaginator

    def get_queryset(self, request: HttpRequest) -> FastCounter:
        """Monkeypatches `count()` to use fast counter."""
        qs = super().get_queryset(request)
        qs.count = qs.fast_count
        return qs
