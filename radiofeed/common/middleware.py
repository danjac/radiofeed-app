from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from radiofeed.common.decorators import lazy_object_middleware, middleware
from radiofeed.common.search import Search
from radiofeed.common.sorter import Sorter
from radiofeed.common.types import GetResponse
from radiofeed.common.user_agent import user_agent


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


search_middleware = lazy_object_middleware("search")(Search)

sorter_middleware = lazy_object_middleware("sorter")(Sorter)

user_agent_middleware = lazy_object_middleware("user_agent")(user_agent)
