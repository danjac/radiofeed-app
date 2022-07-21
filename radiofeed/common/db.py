from __future__ import annotations

import functools
import operator

from typing import TYPE_CHECKING, Iterable, TypeAlias, TypeVar

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import connections
from django.db.models import F, Model, Q, QuerySet
from django.utils.encoding import force_str

_T = TypeVar("_T", bound=Model)


if TYPE_CHECKING:
    _QuerySet: TypeAlias = QuerySet[_T]  # pragma: no cover
else:
    _QuerySet = object


class FastCountMixin(_QuerySet):
    """Provides faster alternative to COUNT for very large tables, using PostgreSQL retuple SELECT.

    Attributes:
        fast_count_row_limit (int): max number of rows before switching from SELECT COUNT to reltuples.
    """

    fast_count_row_limit: int = 1000

    def count(self: _QuerySet) -> int:
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


class SearchMixin(_QuerySet):
    """Provides standard search interface for models supporting search vector and ranking.

    Adds a `search` method to automatically resolve simple PostgreSQL search vector queries.

    Attributes:
        search_vectors: SearchVector fields and ranks (if multiple)
        search_vector_field: single SearchVectorField
        search_rank: SearchRank field for ordering
        search_type: PostgreSQL search type
    """

    search_vectors: list[tuple[str, str]] = []
    search_vector_field: str = "search_vector"
    search_rank: str = "rank"
    search_type: str = "websearch"

    def search(self: _QuerySet, search_term: str) -> _QuerySet:
        """Returns result of search."""
        if not search_term:
            return self.none()

        query = SearchQuery(force_str(search_term), search_type=self.search_type)

        return self.annotate(**dict(self._search_ranks(query))).filter(
            functools.reduce(operator.or_, self._search_filters(query))
        )

    def _search_filters(self, query: SearchQuery) -> Iterable[Q]:

        if self.search_vectors:
            for field, _ in self.search_vectors:
                yield Q(**{field: query})
        else:
            yield Q(**{self.search_vector_field: query})

    def _search_ranks(self, query: SearchQuery) -> Iterable[tuple[str, SearchRank]]:
        if not self.search_vectors:
            yield self.search_rank, SearchRank(F(self.search_vector_field), query=query)
            return

        combined: list[F] = []

        for field, rank in self.search_vectors:
            yield rank, SearchRank(F(field), query=query)

            combined.append(F(rank))

        yield self.search_rank, functools.reduce(operator.add, combined)


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
