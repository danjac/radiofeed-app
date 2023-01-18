from __future__ import annotations

import dataclasses
import enum

from collections.abc import Callable
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str
from django.utils.functional import SimpleLazyObject, cached_property

from radiofeed.http import user_agent


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


class PaginationMiddleware(BaseMiddleware):
    """Adds `Pagination` instance as `request.pagination`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.pagination = Pagination(request)
        return self.get_response(request)


class SearchMiddleware(BaseMiddleware):
    """Adds `Search` instance as `request.search`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.search = Search(request)
        return self.get_response(request)


class OrderingMiddleware(BaseMiddleware):
    """Adds `Ordering` instance as `request.ordering`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.ordering = Ordering(request)
        return self.get_response(request)


class UserAgentMiddleware(BaseMiddleware):
    """Adds `user_agent` string to request. Used to make API calls from a view."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.user_agent = SimpleLazyObject(lambda: user_agent(request))
        return self.get_response(request)


@dataclasses.dataclass(frozen=True)
class Pagination:
    """Handles pagination parameters in request."""

    request: HttpRequest

    param: str = "page"

    def __str__(self) -> str:
        """Returns current page."""
        return self.current

    @cached_property
    def current(self) -> str:
        """Returns current page number from URL."""
        return self.request.GET.get(self.param, "")

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


@dataclasses.dataclass(frozen=True)
class Ordering:
    """Handles ordering parameters in request."""

    class Choices(enum.StrEnum):
        ASC = enum.auto()
        DESC = enum.auto()

    request: HttpRequest

    param: str = "order"
    default: str = Choices.DESC

    def __str__(self) -> str:
        """Returns ordering value."""
        return str(self.value)

    @cached_property
    def value(self) -> Ordering:
        """Returns the search query value, if any."""
        return self.request.GET.get(self.param, self.default)

    @cached_property
    def is_asc(self) -> bool:
        """Returns True if sort ascending."""
        return self.value == self.Choices.ASC

    @cached_property
    def is_desc(self) -> bool:
        """Returns True if sort descending."""
        return self.value == self.Choices.DESC

    @cached_property
    def reverse_qs(self) -> str:
        """Returns ascending query string parameter/value if current url descending and vice versa."""
        return urlencode(
            {self.param: self.Choices.DESC if self.is_asc else self.Choices.ASC}
        )


@dataclasses.dataclass(frozen=True)
class Search:
    """Handles search parameters in request."""

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
