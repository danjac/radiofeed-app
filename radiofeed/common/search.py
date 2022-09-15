from __future__ import annotations

import functools
import operator

from typing import TYPE_CHECKING, TypeAlias, TypeVar
from urllib.parse import urlencode

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Model, Q, QuerySet
from django.http import HttpRequest
from django.utils.encoding import force_str
from django.utils.functional import cached_property

if TYPE_CHECKING:  # pragma: no cover
    _T = TypeVar("_T", bound=Model)
    _QuerySet: TypeAlias = QuerySet[_T]
else:
    _QuerySet = object


class Search:
    """Encapsulates generic search query in a request.

    Attributes:
        param: query string parameter
    """

    param: str = "q"

    def __init__(self, request: HttpRequest):
        self._request = request

    def __str__(self) -> str:
        """Returns search query value."""
        return self.value

    def __bool__(self) -> bool:
        """Returns `True` if search in query and has a non-empty value."""
        return bool(self.value)

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return force_str(self._request.GET.get(self.param, "")).strip()

    @cached_property
    def qs(self) -> str:
        """Returns encoded query string value, if any."""
        return urlencode({self.param: self.value}) if self.value else ""


class SearchQuerySetMixin(_QuerySet):
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

        ranks = {
            rank: SearchRank(F(field), query=query)
            for field, rank in self.search_vectors
        } or {
            self.search_rank: SearchRank(F(self.search_vector_field), query=query),
        }

        if combined := [F(rank) for _, rank in self.search_vectors]:
            ranks[self.search_rank] = functools.reduce(operator.add, combined)

        filters = [Q(**{field: query}) for field, _ in self.search_vectors] or [
            Q(**{self.search_vector_field: query})
        ]

        return self.annotate(**ranks).filter(functools.reduce(operator.or_, filters))
