from __future__ import annotations

import dataclasses

from collections.abc import Iterable
from urllib.parse import urlencode

from django.core import paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.encoding import force_str
from django.utils.functional import SimpleLazyObject, cached_property

from radiofeed.types import GetResponse


class CacheControlMiddleware:
    """Workaround for https://github.com/bigskysoftware/htmx/issues/497.

    Place after HtmxMiddleware.
    """

    def __init__(self, get_response: GetResponse):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        response = self.get_response(request)
        if request.htmx:
            # don't override if cache explicitly set
            response.setdefault("Cache-Control", "no-store, max-age=0")
        return response


class PaginatorMiddleware:
    """Adds `Paginator` instance as `request.paginator`."""

    def __init__(self, get_response: GetResponse):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.paginator = SimpleLazyObject(lambda: Paginator(request))
        return self.get_response(request)


class SearchMiddleware:
    """Adds `Search` instance as `request.search`."""

    def __init__(self, get_response: GetResponse):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)


class SorterMiddleware:
    """Adds `Sorter` instance as `request.sorter`."""

    def __init__(self, get_response: GetResponse):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.sorter = SimpleLazyObject(lambda: Sorter(request))
        return self.get_response(request)


@dataclasses.dataclass(frozen=True)
class Paginator:
    """Wraps pagination functionality."""

    request: HttpRequest

    param: str = "page"
    page_size: int = 30
    target: str = "pagination"

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
        return f"{self.request.path}?{qs.urlencode()}"

    def render(
        self,
        object_list: Iterable,
        template_name: str,
        pagination_template_name: str,
        extra_context: dict | None = None,
    ) -> HttpResponse:
        """Renders paginated response.

        Raises:
            Http404: invalid page number
        """
        try:
            page = paginator.Paginator(object_list, self.page_size).page(
                self.request.GET.get(self.param, 1)
            )

        except paginator.InvalidPage:
            raise Http404

        template_name = (
            pagination_template_name
            if self.request.htmx and self.request.htmx.target == self.target
            else template_name
        )

        return render(
            self.request,
            template_name,
            {
                "page_obj": page,
                "pagination_target": self.target,
                "pagination_template": pagination_template_name,
                **(extra_context or {}),
            },
        )


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
