from __future__ import annotations

from django.db import connections
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


def get_reltuple_count(db: str, table: str) -> int:
    """Returns result of SELECT reltuples.

    Args:
        db: database name
        table: table name

    Returns:
        number of rows
    """
    cursor = connections[db].cursor()
    cursor.execute("SELECT reltuples FROM pg_class WHERE relname = %s", [table])
    return int(cursor.fetchone()[0])
