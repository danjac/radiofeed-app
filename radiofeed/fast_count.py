from typing import Protocol

from django.core.paginator import Paginator
from django.db import connections
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import cached_property


class FastCounter(Protocol):
    """Protocol for QuerySet subclasses or mixins implementing `fast_count()`."""

    def fast_count(self) -> int:
        """Should return an optimized COUNT query."""
        ...  # pragma: no cover


class FastCountQuerySetMixin:
    """Provides faster alternative to COUNT for very large tables, using PostgreSQL
    retuple SELECT.

    Attributes:
        fast_count_row_limit (int): max number of rows before switching from SELECT
        COUNT to reltuples.
    """

    fast_count_row_limit: int = 1000

    def fast_count(self) -> int:
        """Does optimized COUNT.

        If query contains WHERE, DISTINCT or GROUP BY, or number of rows under
        `fast_count_row_limit`, returns standard SELECT COUNT.

        Returns:
            number of rows
        """

        if self._query.distinct or self._query.group_by or self._query.where:
            return super().count()

        count = get_reltuple_count(self.db, self.model._meta.db_table)

        return count if count > self.fast_count_row_limit else super().count()


class FastCountPaginator(Paginator):
    """Paginator that uses `FastCountMixin` queryset for `count()`."""

    object_list: FastCounter

    @cached_property
    def count(self) -> int:
        """Should return optimized count."""
        return self.object_list.fast_count()


class FastCountAdminMixin:
    """Implements fast count. Use with queryset implementing FastCounter."""

    paginator = FastCountPaginator

    def get_queryset(self, request: HttpRequest) -> QuerySet:
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
