from django.http import HttpRequest, HttpResponse

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
