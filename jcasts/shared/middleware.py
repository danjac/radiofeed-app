from __future__ import annotations

from typing import Callable
from urllib.parse import urlencode

from django.contrib.messages.api import get_messages
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.utils.encoding import force_str
from django.utils.functional import SimpleLazyObject, cached_property

from jcasts.shared.htmx import with_hx_trigger


class BaseMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response


class Search:
    search_param: str = "q"

    def __init__(self, request: HttpRequest):
        self.request = request

    def __str__(self) -> str:
        return self.value

    def __bool__(self) -> bool:
        return bool(self.value)

    @cached_property
    def value(self) -> str:
        return force_str(self.request.GET.get(self.search_param, "")).strip()

    @cached_property
    def qs(self) -> str:
        return urlencode({self.search_param: self.value}) if self.value else ""


class SearchMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)


class CacheControlMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # workaround for https://github.com/bigskysoftware/htmx/issues/497
        # place after HtmxMiddleware
        response = self.get_response(request)
        if request.htmx:
            # don't override if cache explicitly set
            response.setdefault("Cache-Control", "no-store, max-age=0")
        return response


class HtmxMessageMiddleware(BaseMiddleware):
    """If htmx request, adds any messages to response
    header to be handled in JS."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if self.use_hx_trigger(request, response) and (
            messages := get_messages(request)
        ):
            return with_hx_trigger(
                response,
                {
                    "messages": [
                        {
                            "message": str(message),
                            "tags": message.tags,
                        }
                        for message in messages
                    ],
                },
            )
        return response

    def use_hx_trigger(self, request: HttpRequest, response: HttpResponse) -> bool:
        return request.htmx and type(response) not in (
            HttpResponseRedirect,
            HttpResponsePermanentRedirect,
        )
