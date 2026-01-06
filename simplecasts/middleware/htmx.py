from typing import Final

from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.cache import patch_vary_headers
from django_htmx.http import HttpResponseLocation

from simplecasts.http.request import HttpRequest
from simplecasts.middleware import BaseMiddleware


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
