import functools
from typing import TypeVar

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, QuerySet

T_QuerySet = TypeVar("T_QuerySet", bound=QuerySet)


def search_queryset(
    queryset: T_QuerySet,
    search_term: str,
    *search_vectors: str,
    search_rank: str = "rank",
    search_type: str = "websearch",
) -> T_QuerySet:
    """Returns result of search, annotated with search rank."""

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
