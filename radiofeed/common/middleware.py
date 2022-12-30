from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from radiofeed.common import user_agent
from radiofeed.common.decorators import lazy_object_middleware, middleware
from radiofeed.common.search import Search
from radiofeed.common.sorter import Sorter


@lazy_object_middleware("user_agent")
def user_agent_middleware(request: HttpRequest) -> str:
    """Appends user agent to request."""
    return user_agent.user_agent(request)


@lazy_object_middleware("search")
def search_middleware(request: HttpRequest) -> Search:
    """Adds Search to request."""
    return Search(request)


@lazy_object_middleware("sorter")
def sorter_middleware(request: HttpRequest) -> Sorter:
    """Adds Sorter to request."""
    return Sorter(request)


@middleware
def cache_control_middleware(
    request: HttpRequest, get_response: Callable
) -> HttpResponse:
    """Workaround for https://github.com/bigskysoftware/htmx/issues/497.

    Place after HtmxMiddleware.
    """
    response = get_response(request)
    if request.htmx:
        # don't override if cache explicitly set
        response.setdefault("Cache-Control", "no-store, max-age=0")
    return response
