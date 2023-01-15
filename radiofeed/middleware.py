from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from radiofeed.decorators import lazy_object_middleware, middleware
from radiofeed.paginator import Paginator
from radiofeed.search import Search
from radiofeed.sorter import Sorter
from radiofeed.types import GetResponse


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


paginator_middleware = lazy_object_middleware("paginator")(Paginator)

search_middleware = lazy_object_middleware("search")(Search)

sorter_middleware = lazy_object_middleware("sorter")(Sorter)
