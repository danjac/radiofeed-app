from __future__ import annotations

import json

from typing import Callable, ClassVar
from urllib.parse import urlencode

from django.contrib.messages.api import get_messages
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.utils.functional import SimpleLazyObject, cached_property


class BaseMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response


class Search:
    search_param: str = "q"
    request: HttpRequest

    def __init__(self, request: HttpRequest):
        self.request = request

    def __str__(self) -> str:
        return self.value

    def __bool__(self) -> bool:
        return bool(self.value)

    @cached_property
    def value(self) -> str:
        return self.request.GET.get(self.search_param, "").strip()

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

    hx_trigger_header: ClassVar[str] = "HX-Trigger"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if self.use_hx_trigger(request, response) and (
            messages := get_messages(request)
        ):
            response[self.hx_trigger_header] = json.dumps(
                {
                    **self.get_hx_trigger(response),
                    "messages": [
                        {
                            "message": str(message),
                            "tags": message.tags,
                        }
                        for message in messages
                    ],
                }
            )
        return response

    def get_hx_trigger(self, response: HttpResponse) -> dict:
        if trigger := response.headers.get(self.hx_trigger_header, None):
            try:
                return json.loads(trigger)
            except json.JSONDecodeError:
                return {trigger: ""}
        return {}

    def use_hx_trigger(self, request: HttpRequest, response: HttpResponse) -> bool:
        return request.htmx and type(response) not in (
            HttpResponseRedirect,
            HttpResponsePermanentRedirect,
        )
