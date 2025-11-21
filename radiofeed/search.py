import functools
from collections.abc import Sequence
from typing import Protocol

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, QuerySet


class Searchable(Protocol):
    """Provide search mixin protocol."""

    search_vectors: Sequence[str]


class SearchQuerySetMixin:
    """Provides standard search interface for models supporting search vector
    and ranking.

    Adds a `search` method to automatically resolve simple PostgreSQL
    search vector queries.
    """

    search_vectors = ("search_vector",)

    def search(
        self: Searchable,
        search_term: str,
        *,
        search_rank: str = "rank",
        search_type: str = "websearch",
    ) -> QuerySet:
        """Returns result of search."""

        if not search_term:
            return self.none()

        query = SearchQuery(search_term, search_type=search_type)

        querysets = (
            self.annotate(
                **{
                    search_rank: SearchRank(F(vector), query=query),
                }
            ).filter(**{vector: query})
            for vector in self.search_vectors
        )

        return functools.reduce(lambda qs1, qs2: qs1.union(qs2), querysets)
