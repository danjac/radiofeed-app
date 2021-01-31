from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject, cached_property

from radiofeed.typing import HttpCallable


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
        return self.request.GET.get(self.search_param, "")


class SearchMiddleware:
    def __init__(self, get_response: HttpCallable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)
