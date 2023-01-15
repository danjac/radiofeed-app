from __future__ import annotations

import dataclasses

from urllib.parse import urlencode

from django.http import HttpRequest
from django.utils.encoding import force_str
from django.utils.functional import cached_property


@dataclasses.dataclass(frozen=True)
class Search:
    """Encapsulates generic search query in a request."""

    request: HttpRequest
    param: str = "query"

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
