from typing import Callable, Optional
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject, cached_property


class BaseMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)


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


# adapted from https://raw.githubusercontent.com/adamchainz/django-htmx/main/src/django_htmx/middleware.py
# when django-htmx gets a release, this can be removed.


class HtmxDetails:
    def __init__(self, request: HttpRequest):
        self.request = request

    def __bool__(self) -> bool:
        return self.is_htmx_request

    @cached_property
    def is_htmx_request(self) -> bool:
        return self.request.headers.get("HX-Request", "") == "true"

    @cached_property
    def current_url(self) -> Optional[str]:
        return self.request.headers.get("HX-Current-URL") or None

    @cached_property
    def prompt(self) -> Optional[str]:
        return self.request.headers.get("HX-Prompt") or None

    @cached_property
    def target(self) -> Optional[str]:
        return self.request.headers.get("HX-Target") or None

    @cached_property
    def trigger(self) -> Optional[str]:
        return self.request.headers.get("HX-Trigger") or None

    @cached_property
    def trigger_name(self) -> Optional[str]:
        return self.request.headers.get("HX-Trigger-Name") or None


class HtmxMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.htmx = SimpleLazyObject(lambda: HtmxDetails(request))
        response = self.get_response(request)
        if request.htmx:
            response["Cache-Control"] = "no-store, max-age=0"
        return response
