from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.decorators import middleware
from radiofeed.common.search import Search
from radiofeed.common.sorter import Sorter
from radiofeed.common.types import GetResponse


@middleware
def search_middleware(request: HttpRequest, get_response: GetResponse) -> HttpResponse:
    """Adds Search instance to request."""
    request.search = SimpleLazyObject(lambda: Search(request))
    return get_response(request)


@middleware
def sorter_middleware(request: HttpRequest, get_response: GetResponse) -> HttpResponse:
    """Adds Sorter instance to request."""
    request.sorter = SimpleLazyObject(lambda: Sorter(request))
    return get_response(request)


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
