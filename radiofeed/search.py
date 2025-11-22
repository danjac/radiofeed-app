import functools
from collections.abc import Sequence
from typing import TypeVar

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Model, QuerySet

T_Model = TypeVar("T_Model", bound=Model)


class SearchQuerySetMixin(QuerySet[T_Model]):
    """Mixin to add full-text search capabilities to a QuerySet."""

    search_vectors: Sequence[str] | str = "search_vector"

    def search(
        self,
        search_term: str,
        search_rank: str = "rank",
        search_type: str = "websearch",
    ) -> QuerySet[T_Model]:
        """Perform a full-text search on the QuerySet using multiple search vectors."""

        if not search_term:
            return self.none()

        query = SearchQuery(
            search_term,
            search_type=search_type,
            config="simple",
        )

        search_vectors = (
            (self.search_vectors,)
            if isinstance(self.search_vectors, str)
            else self.search_vectors
        )

        querysets = (
            self.annotate(
                **{
                    search_rank: SearchRank(F(vector), query=query),
                }
            ).filter(**{vector: query})
            for vector in search_vectors
        )
        return functools.reduce(lambda qs1, qs2: qs1.union(qs2), querysets)
