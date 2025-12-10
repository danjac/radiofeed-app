import functools
import operator
from typing import TYPE_CHECKING, Self

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q, QuerySet

if TYPE_CHECKING:
    BaseQuerySet = QuerySet
else:
    BaseQuerySet = object


class SearchQuerySet(BaseQuerySet):
    """Search queryset mixin."""

    search_fields: tuple[str, ...] = ()

    def search(
        self,
        value: str,
        *search_fields: str,
        annotation: str = "rank",
        config: str = "simple",
        search_type: str = "websearch",
    ) -> Self:
        """Search queryset using full-text search."""

        if not value:
            return self.none()

        search_fields = search_fields or self.search_fields

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

        return self.annotate(**{annotation: rank}).filter(q)
