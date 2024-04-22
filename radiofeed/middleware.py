import enum
from urllib.parse import urlencode

from django.contrib.messages import get_messages
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.utils.cache import patch_vary_headers
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django_htmx.http import HttpResponseLocation

from radiofeed.types import HttpRequestResponse


class HtmxResponseHeadersMiddleware:
    """Workarounds for https://github.com/bigskysoftware/htmx/issues/497.

    Sets Cache-Control and Vary headers to ensure full page is rendered.

    Place after HtmxMiddleware.
    """

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        response = self.get_response(request)
        if request.htmx:
            patch_vary_headers(response, ["HX-Request"])
            response.setdefault("Cache-Control", "no-store, max-age=0")
        return response


class HtmxMessagesMiddleware:
    """Adds messages to HTMX response"""

    _hx_redirect_headers = frozenset(
        {
            "HX-Location",
            "HX-Redirect",
            "HX-Refresh",
        }
    )

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation"""
        response = self.get_response(request)

        if not request.htmx:
            return response

        if set(response.headers) & self._hx_redirect_headers:
            return response

        if get_messages(request):
            response.write(
                render_to_string(
                    template_name="_messages.html",
                    context={"hx_oob": True},
                    request=request,
                )
            )

        return response


class HtmxRedirectMiddleware:
    """If HTMX request will send HX-Location response header if HTTP redirect."""

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation"""
        response = self.get_response(request)
        if request.htmx and "Location" in response:
            return HttpResponseLocation(response["Location"])
        return response


class PaginationMiddleware:
    """Adds `Pagination` instance as `request.pagination`."""

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.pagination = PaginationDetails(request)
        return self.get_response(request)


class SearchMiddleware:
    """Adds `Search` instance as `request.search`."""

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.search = SearchDetails(request)
        return self.get_response(request)


class OrderingMiddleware:
    """Adds `Ordering` instance as `request.ordering`."""

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.ordering = OrderingDetails(request)
        return self.get_response(request)


class PaginationDetails:
    """Handles pagination parameters in request."""

    param: str = "page"

    def __init__(self, request: HttpRequest) -> None:
        self.request = request

    def __str__(self) -> str:
        """Returns current page."""
        return self.current

    @cached_property
    def current(self) -> str:
        """Returns current page number from query string."""
        return self.request.GET.get(self.param, "")

    def url(self, page_number: int) -> str:
        """Inserts the page query string parameter with the provided page number into
        the current query string.

        Preserves the original request path and any other query string parameters.
        """
        qs = self.request.GET.copy()
        qs[self.param] = page_number
        return f"{self.request.path}?{qs.urlencode()}"


class SearchDetails:
    """Handles search parameters in request."""

    param: str = "query"

    def __init__(self, request: HttpRequest) -> None:
        self.request = request

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


class OrderingDetails:
    """Handles ordering parameters in request."""

    class Choices(enum.StrEnum):
        ASC = enum.auto()
        DESC = enum.auto()

    param: str = "order"
    default: str = Choices.DESC

    def __init__(self, request: HttpRequest) -> None:
        self.request = request

    def __str__(self) -> str:
        """Returns ordering value."""
        return str(self.value)

    @cached_property
    def value(self) -> str:
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
    def qs_reversed(self) -> str:
        """Returns ascending query string parameter/value if current url descending
        and vice versa."""
        return urlencode(
            {self.param: self.Choices.DESC if self.is_asc else self.Choices.ASC}
        )
