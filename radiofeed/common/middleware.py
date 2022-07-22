from __future__ import annotations

from typing import Callable, cast
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str
from django.utils.functional import SimpleLazyObject, cached_property


class BaseMiddleware:
    """Convenient base class for custom middleware."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response


class Search:
    """Encapsulates generic search query.

    Attributes:
        search_param: query string parameter
    """

    search_param: str = "search"

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
        return force_str(self._request.GET.get(self.search_param, "")).strip()

    @cached_property
    def qs(self) -> str:
        """Returns encoded query string value, if any."""
        return urlencode({self.search_param: self.value}) if self.value else ""


class SearchMiddleware(BaseMiddleware):
    """Adds Search instance to the request as `request.search`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Adds Search instance to request."""
        request.search = cast(Search, SimpleLazyObject(lambda: Search(request)))
        return self.get_response(request)


class CacheControlMiddleware(BaseMiddleware):
    """Workaround for https://github.com/bigskysoftware/htmx/issues/497.

    Place after HtmxMiddleware
    """

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Resolves middleware."""
        response = self.get_response(request)
        if request.htmx:
            # don't override if cache explicitly set
            response.setdefault("Cache-Control", "no-store, max-age=0")
        return response
