import functools
import operator
from typing import TypeVar

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Model, Q, QuerySet

T = TypeVar("T")
T_Model = TypeVar("T_Model", bound=Model)
T_QuerySet = TypeVar("T_QuerySet", bound=QuerySet)


def search_queryset(
    queryset: T_QuerySet,
    value: str,
    *search_fields: str,
    annotation: str = "rank",
    config: str = "simple",
    search_type: str = "websearch",
) -> T_QuerySet:
    """Search a given QuerySet using full-text search."""
    if not search_fields:
        raise ValueError("At least one search vector field must be provided")

    if not value:
        return queryset.none()

    query = SearchQuery(value, search_type=search_type, config=config)

    rank = functools.reduce(
        operator.add,
        (
            SearchRank(
                F(field),
                query=query,
            )
            for field in search_fields
        ),
    )

    q = functools.reduce(
        operator.or_,
        (
            Q(
                **{field: query},
            )
            for field in search_fields
        ),
    )

    return queryset.annotate(**{annotation: rank}).filter(q)
