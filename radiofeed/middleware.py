from __future__ import annotations

import dataclasses

from collections.abc import Callable
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str
from django.utils.functional import SimpleLazyObject, cached_property


class BaseMiddleware:
    """Base middleware class."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response


class CacheControlMiddleware(BaseMiddleware):
    """Workaround for https://github.com/bigskysoftware/htmx/issues/497.

    Place after HtmxMiddleware.
    """

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        response = self.get_response(request)
        if request.htmx:
            # don't override if cache explicitly set
            response.setdefault("Cache-Control", "no-store, max-age=0")
        return response


class CurrentPageMiddleware(BaseMiddleware):
    """Adds `Page` instance as `request.page`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.page = SimpleLazyObject(lambda: Page(request))
        return self.get_response(request)


class SearchMiddleware(BaseMiddleware):
    """Adds `Search` instance as `request.search`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)


class SorterMiddleware(BaseMiddleware):
    """Adds `Sorter` instance as `request.sorter`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.sorter = SimpleLazyObject(lambda: Sorter(request))
        return self.get_response(request)


@dataclasses.dataclass(frozen=True)
class Page:
    """Wraps pagination request query functionality."""

    request: HttpRequest

    param: str = "page"

    def __str__(self) -> str:
        """Returns current page."""
        return self.current

    def url(self, page_number: int) -> str:
        """Inserts the page query string parameter with the provided page number into the template.

        Preserves the original request path and any other query string parameters.

        Given the above and a URL of "/search?q=test" the result would
        be something like: "/search?q=test&p=3"

        Returns:
            updated URL path with new page
        """
        qs = self.request.GET.copy()
        qs[self.param] = page_number
        return self.request.path + "?" + qs.urlencode()

    @cached_property
    def current(self) -> str:
        """Returns current page number from URL."""
        return self.request.GET.get(self.param, "1")


@dataclasses.dataclass(frozen=True)
class Sorter:
    """Encapsulates sorting/ordering functionality."""

    request: HttpRequest

    asc: str = "asc"
    desc: str = "desc"

    param: str = "order"
    default: str = "desc"

    def __str__(self) -> str:
        """Returns ordering value."""
        return self.value

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return self.request.GET.get(self.param, self.default)

    @cached_property
    def is_asc(self) -> bool:
        """Returns True if sort ascending."""
        return self.value == self.asc

    @cached_property
    def is_desc(self) -> bool:
        """Returns True if sort descending."""
        return self.value == self.desc

    @cached_property
    def qs(self) -> str:
        """Returns ascending query string parameter/value if current url descending and vice versa."""
        return urlencode({self.param: self.desc if self.is_asc else self.asc})


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
