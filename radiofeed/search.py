import functools
import operator
from typing import ClassVar, Protocol

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q, QuerySet


class Searchable(Protocol):
    """Provide search mixin protocol."""

    search_vectors: list[tuple[str, str]]
    search_vector_field: str
    search_rank: str
    search_type: str


class SearchQuerySetMixin:
    """Provides standard search interface for models supporting search vector
    and ranking.

    Adds a `search` method to automatically resolve simple PostgreSQL
    search vector queries.

    Attributes:
        search_vectors: SearchVector fields and ranks (if multiple)
        search_vector_field: single SearchVectorField
        search_rank: SearchRank field for ordering
        search_type: PostgreSQL search type
    """

    search_vectors: ClassVar[list[tuple[str, str]]] = []
    search_vector_field: str = "search_vector"
    search_rank: str = "rank"
    search_type: str = "websearch"

    def search(self: Searchable, search_term: str) -> QuerySet:
        """Returns result of search."""

        if not search_term:
            return self.none()

        query = SearchQuery(search_term, search_type=self.search_type)

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
