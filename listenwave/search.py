import functools
import operator
from typing import TYPE_CHECKING, Self

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q

if TYPE_CHECKING:
    from django.db.models import QuerySet

    QuerySetMixin = QuerySet
else:
    QuerySetMixin = object


class SearchableMixin(QuerySetMixin):
    """A QuerySet mixin that adds full-text search capabilities to Django models."""

    # Default assumption: the model has a 'search_vector' field.
    search_fields: tuple[str, ...] = ("search_vector",)

    def search(
        self,
        value: str,
        *search_fields: str,
        annotation: str = "rank",
        config: str = "simple",
        search_type: str = "websearch",
    ) -> Self:
        """Perform a full-text search on the given QuerySet using one or more search vectors.
        Results are annotated with a rank based on relevance to the search query.
        """

        if not value:
            return self.none()

        query = SearchQuery(
            value,
            search_type=search_type,
            config=config,
        )

        search_fields = search_fields or self.search_fields

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

        return self.annotate(**{annotation: rank}).filter(q)
