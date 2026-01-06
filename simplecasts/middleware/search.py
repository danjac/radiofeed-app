import dataclasses

from django.http import HttpResponse, QueryDict
from django.utils.encoding import force_str
from django.utils.functional import cached_property

from simplecasts.http.request import HttpRequest
from simplecasts.middleware import BaseMiddleware


class SearchMiddleware(BaseMiddleware):
    """Adds `SearchDetails` instance as `request.search`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.search = SearchDetails(request=request)
        return self.get_response(request)


@dataclasses.dataclass(frozen=True, kw_only=True)
class SearchDetails:
    """Handles search parameters in request."""

    request: HttpRequest
    param: str = "search"
    max_length: int = 200

    def __str__(self) -> str:
        """Returns search query value."""
        return self.value

    def __bool__(self) -> bool:
        """Returns `True` if search in query and has a non-empty value."""
        return bool(self.value)

    @cached_property
    def value(self) -> str:
        """Returns the search query value, if any."""
        return force_str(self.request.GET.get(self.param, "")).strip()[
            : self.max_length
        ]

    @cached_property
    def qs(self) -> str:
        """Returns querystring with search."""
        return (
            "?" + QueryDict.fromkeys([self.param], value=self.value).urlencode()
            if self
            else ""
        )
