from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.decorators import middleware
from radiofeed.common.paginator import Paginator
from radiofeed.common.search import Search
from radiofeed.common.sorter import Sorter
from radiofeed.common.types import GetResponse


@middleware
def cache_control_middleware(
    request: HttpRequest, get_response: GetResponse
) -> HttpResponse:
    """Workaround for https://github.com/bigskysoftware/htmx/issues/497.

    Place after HtmxMiddleware.
    """
    response = get_response(request)
    if request.htmx:
        # don't override if cache explicitly set
        response.setdefault("Cache-Control", "no-store, max-age=0")
    return response


def lazy_object_middleware(fn: Callable[[HttpRequest], Any], attr: str) -> GetResponse:
    """Appends a lazy object to request mapped to `attr`."""

    @middleware
    def _middleware(request: HttpRequest, get_response: GetResponse) -> HttpResponse:
        setattr(request, attr, SimpleLazyObject(lambda: fn(request)))
        return get_response(request)

    return _middleware


paginator_middleware = lazy_object_middleware(Paginator, "paginator")

search_middleware = lazy_object_middleware(Search, "search")

sorter_middleware = lazy_object_middleware(Sorter, "sorter")
