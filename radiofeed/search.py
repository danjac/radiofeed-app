import functools
from typing import TypeVar

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Model, QuerySet

T_Model = TypeVar("T_Model", bound=Model)


def search_queryset(
    queryset: QuerySet[T_Model],
    search_term: str,
    *search_vectors: str,
    search_rank: str = "rank",
    search_type: str = "websearch",
) -> QuerySet[T_Model]:
    """
    Perform a full-text search on the given queryset using multiple search vectors.
    """

    if not search_term:
        return queryset.none()

    query = SearchQuery(search_term, search_type=search_type)

    querysets = (
        queryset.annotate(
            **{
                search_rank: SearchRank(F(vector), query=query),
            }
        ).filter(**{vector: query})
        for vector in search_vectors
    )

    return functools.reduce(lambda qs1, qs2: qs1.union(qs2), querysets)
