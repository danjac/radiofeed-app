from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeAlias, TypeVar

from django.contrib import admin
from django.core.paginator import Paginator
from django.db import connections
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.utils.functional import cached_property

if TYPE_CHECKING:  # pragma: no cover
    _T = TypeVar("_T", bound=Model)
    _QuerySet: TypeAlias = QuerySet[_T]
    _ModelAdmin: TypeAlias = admin.ModelAdmin
else:
    _ModelAdmin = object
    _QuerySet = object


class FastCounter(Protocol):
    """Protocol for QuerySet subclasses or mixins implementing `fast_count()`."""

    def fast_count(self) -> int:
        """Should return an optimized COUNT query."""
        ...  # pragma: no cover


class FastCountQuerySetMixin(FastCounter, _QuerySet):
    """Provides faster alternative to COUNT for very large tables, using PostgreSQL retuple SELECT.

    Attributes:
        fast_count_row_limit (int): max number of rows before switching from SELECT COUNT to reltuples.
    """

    fast_count_row_limit: int = 1000

    def fast_count(self: _QuerySet) -> int:
        """Does optimized COUNT.

        If query contains WHERE, DISTINCT or GROUP BY, or number of rows under `fast_count_row_limit`, returns standard SELECT COUNT.

        Returns:
            number of rows
        """
        if any(
            (
                self._query.distinct,
                self._query.group_by,
                self._query.where,
            )
        ) or self.fast_count_row_limit > (
            count := get_reltuple_count(self.db, self.model._meta.db_table)
        ):
            return super().count()

        return count


class FastCountPaginator(Paginator):
    """Paginator that uses `FastCountMixin` queryset for `count()`."""

    object_list: FastCounter

    @cached_property
    def count(self) -> int:
        """Should return optimized count."""
        return self.object_list.fast_count()


class FastCountAdminMixin(_ModelAdmin):
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
