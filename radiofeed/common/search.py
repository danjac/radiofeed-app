from __future__ import annotations

import dataclasses
import functools
import operator

from typing import Protocol
from urllib.parse import urlencode

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q
from django.http import HttpRequest
from django.utils.encoding import force_str
from django.utils.functional import cached_property

from radiofeed.common.types import T_QuerySet


class Searchable(Protocol):
    """Protocol for `search()` method."""

    def search(self, search_term: str) -> T_QuerySet:  # pragma: no cover
        """Signature of search method."""
        ...


@dataclasses.dataclass(frozen=True)
class Search:
    """Encapsulates generic search query in a request."""

    request: HttpRequest
    param: str = "q"

    def __str__(self) -> str:
        """Returns search query value."""
        return self.value

    def __bool__(self) -> bool:
        """Returns `True` if search in query and has a non-empty value."""
        return bool(self.value)

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return force_str(self.request.GET.get(self.param, "")).strip()

    @cached_property
    def qs(self) -> str:
        """Returns encoded query string value, if any."""
        return urlencode({self.param: self.value}) if self.value else ""

    def filter_queryset(self, queryset: Searchable) -> T_QuerySet:
        """Does search on queryset."""
        return queryset.search(self.value)


class SearchQuerySetMixin(Searchable, T_QuerySet):
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

    def search(self: T_QuerySet, search_term: str) -> T_QuerySet:
        """Returns result of search."""
        if not search_term:
            return self.none()

        query = SearchQuery(force_str(search_term), search_type=self.search_type)

        if self.search_vectors:

            return self.annotate(
                **{
                    **{
                        rank: SearchRank(F(field), query=query)
                        for field, rank in self.search_vectors
                    },
                    self.search_rank: functools.reduce(
                        operator.add,
                        [F(rank) for _, rank in self.search_vectors],
                    ),
                }
            ).filter(
                functools.reduce(
                    operator.or_,
                    [Q(**{field: query}) for field, _ in self.search_vectors],
                )
            )

        return self.annotate(
            **{
                self.search_rank: SearchRank(
                    F(self.search_vector_field),
                    query=query,
                ),
            }
        ).filter(**{self.search_vector_field: query})
