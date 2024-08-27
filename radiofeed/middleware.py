from django.http import HttpRequest, HttpResponse, QueryDict
from django.utils.encoding import force_str
from django.utils.functional import cached_property

from radiofeed.types import HttpRequestResponse


class BaseMiddleware:
    """Base middleware class."""

    def __init__(self, get_response: HttpRequestResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware callable."""
        return self.handle_request(request)

    def handle_request(self, request: HttpRequest) -> HttpResponse:
        """Implementation."""
        raise NotImplementedError  # pragma: no cover


class SearchMiddleware(BaseMiddleware):
    """Adds `SearchDetails` instance as `request.search`."""

    def handle_request(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.search = SearchDetails(request)
        return self.get_response(request)


class SearchDetails:
    """Handles search parameters in request."""

    param: str = "search"

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
        """Returns querystring with search."""
        return (
            "?" + QueryDict.fromkeys([self.param], value=self.value).urlencode()
            if self
            else ""
        )
