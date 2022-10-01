from __future__ import annotations

from typing import Callable, cast

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.search import Search
from radiofeed.common.sorter import Sorter


class BaseMiddleware:
    """Convenient base class for custom middleware."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response


class SearchMiddleware(BaseMiddleware):
    """Adds Search instance to the request as `request.search`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Adds Search instance to request."""
        request.search = cast(Search, SimpleLazyObject(lambda: Search(request)))
        return self.get_response(request)


class SorterMiddleware(BaseMiddleware):
    """Adds Sorter instance to the request as `request.sorter`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Adds Sorter instance to request."""
        request.sorter = cast(Sorter, SimpleLazyObject(lambda: Sorter(request)))
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
