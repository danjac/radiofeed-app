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
        self.param = param
        self.default = default

    def __str__(self) -> str:
        """Returns search query value."""
        return self.value

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return self._request.GET.get(self.param, self.default)

    @cached_property
    def is_asc(self):
        """Returns True if sort ascending."""
        return self.value == self._asc

    @cached_property
    def is_desc(self):
        """Returns True if sort descending."""
        return self.value == self._desc

    @cached_property
    def asc_url(self):
        """Returns url with ascending param."""
        return self._make_url(self._asc)

    @cached_property
    def desc_url(self):
        """Returns url with descending param."""
        return self._make_url(self._desc)

    @cached_property
    def url(self):
        """Returns ascending url if current url descending and vice versa."""
        return self.desc_url if self.is_asc else self.asc_url

    def order_by(self, queryset: QuerySet, *fields: str) -> QuerySet:
        """Orders queryset by fields."""
        return queryset.order_by(
            *["-" + field if self.is_desc else field for field in fields]
        )

    def _make_url(self, ordering: str):
        return f"{self._request.path}?{urlencode({self.param: ordering})}"
