import functools
import operator
from typing import TYPE_CHECKING, TypeAlias

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q, QuerySet

if TYPE_CHECKING:
    Base: TypeAlias = QuerySet

else:
    Base = object


class Searchable(Base):
    """Mixin to add full-text search capabilities to Django models."""

    default_search_fields: tuple[str, ...] = ()

    def search(
        self,
        value: str,
        *search_fields: str,
        annotation: str = "rank",
        config: str = "simple",
        search_type: str = "websearch",
    ) -> QuerySet:
        """Search the model's default manager queryset using full-text search."""
        if not value:
            return self.none()

        search_fields = search_fields if search_fields else self.default_search_fields
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
