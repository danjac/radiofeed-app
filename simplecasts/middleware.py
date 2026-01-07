import dataclasses
from collections.abc import Callable
from typing import Final

from django.contrib.messages import get_messages
from django.http import HttpResponse, QueryDict
from django.template.loader import render_to_string
from django.utils.cache import patch_vary_headers
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django_htmx.http import HttpResponseLocation

from simplecasts.http.request import HttpRequest


@dataclasses.dataclass(frozen=True, kw_only=False)
class BaseMiddleware:
    """Base middleware class."""

    get_response: Callable[[HttpRequest], HttpResponse]


class HtmxCacheMiddleware(BaseMiddleware):
    """See https://htmx.org/docs/#caching

    Sets the Vary header to include "HX-Request" for all HTMX requests.

    Place after HtmxMiddleware.
    """

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        response = self.get_response(request)
        if request.htmx:
            patch_vary_headers(response, ("HX-Request",))
        return response


class HtmxMessagesMiddleware(BaseMiddleware):
    """Adds messages to HTMX response"""

    _hx_redirect_headers: Final = frozenset(
        {
            "HX-Location",
            "HX-Redirect",
            "HX-Refresh",
        }
    )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation"""
        response = self.get_response(request)

        if response.streaming:
            return response

        if not request.htmx:
            return response

        if "text/html" not in response.get("Content-Type", ""):
            return response

        if set(response.headers) & self._hx_redirect_headers:
            return response

        if messages := get_messages(request):
            response.write(
                render_to_string(
                    "messages.html",
                    {
                        "messages": messages,
                        "hx_oob": True,
                    },
                    request=request,
                )
            )

        return response


class HtmxRedirectMiddleware(BaseMiddleware):
    """If HTMX request will send HX-Location response header if HTTP redirect."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation"""
        response = self.get_response(request)
        if request.htmx and "Location" in response:
            return HttpResponseLocation(response["Location"])
        return response


class PlayerMiddleware(BaseMiddleware):
    """Adds `PlayerDetails` instance to request as `request.player`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.player = PlayerDetails(request=request)
        return self.get_response(request)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PlayerDetails:
    """Tracks current player episode in session."""

    request: HttpRequest
    session_id: str = "audio-player"

    def get(self) -> int | None:
        """Returns primary key of episode in player, if any in session."""
        return self.request.session.get(self.session_id)

    def has(self, episode_id: int) -> bool:
        """Checks if episode matching ID is in player."""
        return self.get() == episode_id

    def set(self, episode_id: int) -> None:
        """Adds episode PK to player in session."""
        self.request.session[self.session_id] = episode_id

    def pop(self) -> int | None:
        """Returns primary key of episode in player, if any in session, and removes
        the episode ID from the session."""
        return self.request.session.pop(self.session_id, None)


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
