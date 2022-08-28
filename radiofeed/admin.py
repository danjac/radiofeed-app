from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from radiofeed.db import FastCounter
from radiofeed.pagination import FastCountPaginator

if TYPE_CHECKING:  # pragma: no cover
    _ModelAdmin: TypeAlias = admin.ModelAdmin
else:
    _ModelAdmin = object


class FastCountAdminMixin(_ModelAdmin):
    """Implements fast count. Use with queryset implementing FastCounter."""

    paginator = FastCountPaginator

    def get_queryset(self, request: HttpRequest) -> QuerySet[FastCounter]:
        """Monkeypatches `count()` to use fast counter."""
        qs = super().get_queryset(request)
        qs.count = qs.fast_count
        return qs
