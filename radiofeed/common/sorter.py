from __future__ import annotations

import dataclasses

from urllib.parse import urlencode

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import cached_property


@dataclasses.dataclass(frozen=True)
class Sorter:
    """Encapsulates sorting/ordering functionality."""

    request: HttpRequest

    asc: str = "asc"
    desc: str = "desc"

    param: str = "o"
    default: str = "desc"

    def __str__(self) -> str:
        """Returns ordering value."""
        return self.value

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return self.request.GET.get(self.param, self.default)

    @cached_property
    def is_asc(self) -> bool:
        """Returns True if sort ascending."""
        return self.value == self.asc

    @cached_property
    def is_desc(self) -> bool:
        """Returns True if sort descending."""
        return self.value == self.desc

    @cached_property
    def qs(self) -> str:
        """Returns ascending query string parameter/value if current url descending and vice versa."""
        return urlencode({self.param: self.desc if self.is_asc else self.asc})

    def order_by(self, queryset: QuerySet, *fields: str) -> QuerySet:
        """Orders queryset by fields."""
        return queryset.order_by(
            *["-" + field if self.is_desc else field for field in fields]
        )
