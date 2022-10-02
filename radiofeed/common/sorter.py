from __future__ import annotations

from urllib.parse import urlencode

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import cached_property


class Sorter:
    """Encapsulates sorting/ordering functionality."""

    _asc: str = "asc"
    _desc: str = "desc"

    def __init__(self, request: HttpRequest, param: str = "o", default: str = "desc"):
        self._request = request
        self._param = param
        self._default = default

    def __str__(self) -> str:
        """Returns ordering value."""
        return self.value

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return self._request.GET.get(self._param, self._default)

    @cached_property
    def is_asc(self) -> bool:
        """Returns True if sort ascending."""
        return self.value == self._asc

    @cached_property
    def is_desc(self) -> bool:
        """Returns True if sort descending."""
        return self.value == self._desc

    @cached_property
    def qs(self) -> str:
        """Returns ascending url if current url descending and vice versa."""
        return urlencode({self._param: self._desc if self.is_asc else self._asc})

    def order_by(self, queryset: QuerySet, *fields: str) -> QuerySet:
        """Orders queryset by fields."""
        return queryset.order_by(
            *["-" + field if self.is_desc else field for field in fields]
        )
